# Dockerfile

# 阶段1：使用官方的Python基础镜像
FROM python:3.11

# 设置环境变量，确保输出能立刻看到，且不产生.pyc文件
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# 在容器内创建一个目录用于存放项目代码
WORKDIR /app

# 复制依赖定义文件
# 这一步可以利用Docker的层缓存，只有当requirements.txt变化时才会重新安装
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -i https://mirrors.aliyun.com/pypi/simple/ -r requirements.txt

# 复制项目中的所有文件到工作目录
# 这是最关键的一步，它会把 alembic.ini, alembic/, app/, .env 等所有东西都复制进去
COPY . .

# 暴露Streamlit应用端口
EXPOSE 8501

# 设置当容器启动时默认执行的命令 (docker-compose up 时会用到)
CMD ["streamlit", "run", "app/main.py", "--server.port=8501", "--server.address=0.0.0.0"]