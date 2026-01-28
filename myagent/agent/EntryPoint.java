package agent;

import java.lang.instrument.Instrumentation;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.stream.Collectors;
import py4j.GatewayServer;

import java.lang.reflect.*;

public class EntryPoint {
    static Instrumentation GLOBAL_INST;

    public static void premain(String args, Instrumentation instrumentation) {
        GLOBAL_INST = instrumentation;
        SocketLogger.init();
        new GatewayServer(new Entry(instrumentation)).start();
        System.out.println("[Agent] Py4J + ready on port 25333");
    }
}

class Entry {
    private final Instrumentation inst;
    private volatile Map<String, Class<?>> classCache = null;

    public Entry(Instrumentation inst) {
        this.inst = inst;
    }
    // ========== 类信息查询 ==========
    public List<String> getAllClassesName() {
        return Arrays.stream(inst.getAllLoadedClasses())
            .map(Class::getName)
            .sorted()
            .toList();
    }

    public void refreshClassCache() {
        synchronized (this) {
            classCache = buildClassCache();
        }
    }

    public Class<?> getClass(String name) throws Exception {
        Map<String, Class<?>> cache = classCache;
        if (cache == null) {
            synchronized (this) {
                cache = classCache;
                if (cache == null) {
                    cache = buildClassCache();
                    classCache = cache;
                }
            }
        }
        Class<?> clazz = cache.get(name);
        if (clazz == null) {
            throw new Exception("Class not found: " + name);
        }
        return clazz;
    }

    public String getClassName(Object obj) {
        return obj == null ? "null" : obj.getClass().getName();
    }

    // ========== 方法调用 ==========
    public Object invokeStaticMethod(String className, String methodName, Object... args) throws Exception {
        Class<?> clazz = getClass(className);
        Method method = findBestMethod(clazz, methodName, args);
        method.setAccessible(true);
        return method.invoke(null, args);
    }

    public Object invokeStaticMethodNoArgs(String className, String methodName) throws Exception {
        Class<?> clazz = getClass(className);
        Method method = clazz.getDeclaredMethod(methodName);
        method.setAccessible(true);
        return method.invoke(null);
    }

    public Object invokeMethod(Object obj, String methodName, Object... args) throws Exception {
        if (obj == null) throw new IllegalArgumentException("Object is null");
        Method method = findBestMethod(obj.getClass(), methodName, args);
        method.setAccessible(true);
        return method.invoke(obj, args);
    }

    public Object invokeMethodNoArgs(Object obj, String methodName) throws Exception {
        if (obj == null) throw new IllegalArgumentException("Object is null");
        Method method = obj.getClass().getDeclaredMethod(methodName);
        method.setAccessible(true);
        return method.invoke(obj);
    }

    // ========== 字段读写 ==========
    public Object readStaticField(String className, String fieldName) throws Exception {
        Class<?> clazz = getClass(className);
        Field field = clazz.getDeclaredField(fieldName);
        field.setAccessible(true);
        return field.get(null);
    }

    public Object readField(Object obj, String fieldName) throws Exception {
        if (obj == null) throw new IllegalArgumentException("Object is null");
        Field field = findField(obj.getClass(), fieldName);
        field.setAccessible(true);
        return field.get(obj);
    }

    public void writeField(Object obj, String fieldName, Object value) throws Exception {
        if (obj == null) throw new IllegalArgumentException("Object is null");
        Field field = findField(obj.getClass(), fieldName);
        field.setAccessible(true);
        field.set(obj, value);
    }

    public void writeStaticField(String className, String fieldName, Object value) throws Exception {
        Class<?> clazz = getClass(className);
        Field field = clazz.getDeclaredField(fieldName);
        field.setAccessible(true);
        field.set(null, value);
    }

    // ========== 辅助方法 ==========
    private Method findBestMethod(Class<?> clazz, String methodName, Object[] args) throws NoSuchMethodException {
        // 尝试精确匹配
        Class<?>[] argTypes = new Class[args.length];
        for (int i = 0; i < args.length; i++) {
            argTypes[i] = boxPrimitive(args[i] == null ? Object.class : args[i].getClass());
        }
        try {
            return clazz.getMethod(methodName, argTypes);
        } catch (NoSuchMethodException e) {
            // 尝试 declared methods（包括 private）
            try {
                return clazz.getDeclaredMethod(methodName, argTypes);
            } catch (NoSuchMethodException ex) {
                // 最后：模糊匹配（只匹配数量，不匹配类型）——用于探索
                for (Method m : clazz.getMethods()) {
                    if (m.getName().equals(methodName) && m.getParameterCount() == args.length) {
                        return m;
                    }
                }
                for (Method m : clazz.getDeclaredMethods()) {
                    if (m.getName().equals(methodName) && m.getParameterCount() == args.length) {
                        return m;
                    }
                }
                throw new NoSuchMethodException("No method " + methodName + " with " + args.length + " params in " + clazz.getName());
            }
        }
    }

    private Field findField(Class<?> clazz, String fieldName) throws NoSuchFieldException {
        try {
            return clazz.getField(fieldName); // public
        } catch (NoSuchFieldException e) {
            return clazz.getDeclaredField(fieldName); // any
        }
    }

    // 处理 int -> Integer 等
    private Class<?> boxPrimitive(Class<?> c) {
        if (c == int.class) return Integer.class;
        if (c == boolean.class) return Boolean.class;
        if (c == long.class) return Long.class;
        if (c == float.class) return Float.class;
        if (c == double.class) return Double.class;
        if (c == byte.class) return Byte.class;
        if (c == char.class) return Character.class;
        if (c == short.class) return Short.class;
        return c;
    }

    private Map<String, Class<?>> buildClassCache() {
        System.out.println("[Agent] Building class cache...");
        Map<String, Class<?>> map = new ConcurrentHashMap<>();
        for (Class<?> clazz : inst.getAllLoadedClasses()) {
            map.put(clazz.getName(), clazz);
        }
        System.out.println("[Agent] Cached " + map.size() + " classes.");
        return map;
    }

    // ========== 原有方法（保留）==========
    public List<String> getPublicMethods(String className) throws Exception {
        Class<?> clazz = getClass(className);
        return Arrays.stream(clazz.getMethods())
            .map(this::formatMethod)
            .sorted()
            .distinct()
            .toList();
    }

    public List<String> getDeclaredMethods(String className) throws Exception {
        Class<?> clazz = getClass(className);
        return Arrays.stream(clazz.getDeclaredMethods())
            .map(this::formatMethod)
            .sorted()
            .toList();
    }

    private String formatMethod(Method m) {
        String params = Arrays.stream(m.getParameterTypes())
            .map(Class::getName)
            .collect(Collectors.joining(", "));
        return m.getReturnType().getSimpleName() + " " + m.getName() + "(" + params + ")";
    }
}