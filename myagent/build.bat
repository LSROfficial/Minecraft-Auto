chcp 65001
@echo off
cd /d "%~dp0"

echo === 1. 编译 ===
javac -cp "py4j-0.10.9.9.jar" agent/*.java
if errorlevel 1 goto :fail

echo === 2. 打包 fat-agent ===
jar cvmf MANIFEST.MF mc-agent.jar -C . agent -C . py4j -C . META-INF
if errorlevel 1 goto :fail

echo === 3. 完成 ===
echo [OK] mc-agent.jar 已更新
goto :eof

:fail
echo [ERR] 构建失败
exit /b 1