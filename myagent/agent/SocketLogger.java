// agent/SocketLogger.java
package agent;

import java.io.*;
import java.net.*;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class SocketLogger {
    private static final int PORT = 25334;
    private static volatile OutputStream socketOut = null; // ← 改成 OutputStream
    private static final Object lock = new Object();
    private static final ExecutorService executor = Executors.newCachedThreadPool();

    public static void init() {
        executor.submit(() -> {
            try (ServerSocket serverSocket = new ServerSocket(PORT)) {
                System.out.println("[Agent] 日志 Socket 服务已启动，等待 Python 连接...");
                while (!Thread.interrupted()) {
                    Socket client = serverSocket.accept();
                    System.out.println("[Agent] Python 客户端已连接");

                    synchronized (lock) {
                        if (socketOut != null) {
                            try { socketOut.close(); } catch (IOException ignored) {}
                        }
                        socketOut = client.getOutputStream(); // ← 直接拿 OutputStream
                    }

                    // 监控客户端断开（可选）
                    executor.submit(() -> {
                        try {
                            byte[] buf = new byte[1];
                            while (client.getInputStream().read(buf) != -1) {
                                // keep alive
                            }
                        } catch (IOException ignored) {}
                        System.out.println("[Agent] Python 客户端断开");
                        synchronized (lock) {
                            if (socketOut != null) {
                                try { socketOut.close(); } catch (IOException ignored) {}
                                socketOut = null;
                            }
                        }
                    });
                }
            } catch (IOException e) {
                e.printStackTrace();
            }
        });

        // 替换 System.out/err → 仍然需要 PrintStream 包装，因为 System.setOut 要求 PrintStream
        System.setOut(new PrintStream(new DualOutputStream(System.out), true));
        System.setErr(new PrintStream(new DualOutputStream(System.err), true));
    }

    static class DualOutputStream extends OutputStream {
        private final OutputStream original;

        DualOutputStream(OutputStream original) {
            this.original = original;
        }

        @Override
        public void write(int b) throws IOException {
            // 写原始输出（如控制台）
            original.write(b);

            // 原样转发原始字节到 socket（不经过任何字符编码！）
            synchronized (lock) {
                if (socketOut != null) {
                    try {
                        socketOut.write(b);      // ← 直接写字节
                        socketOut.flush();       // ← 立即发送，避免缓冲
                    } catch (IOException e) {
                        // 连接断开，清理
                        try { socketOut.close(); } catch (Exception ignored) {}
                        socketOut = null;
                    }
                }
            }
        }

        @Override
        public void flush() throws IOException {
            original.flush();
            // socketOut 的 flush 已在 write 中调用，这里可省略
        }
    }
}