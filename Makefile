.PHONY: help run build install setup test

help: ## 显示帮助信息
	@echo "今天吃什么 — 可用命令："
	@echo "  make install  安装依赖"
	@echo "  make build    构建前端并复制到后端静态目录"
	@echo "  make run      启动后端服务"
	@echo "  make test     运行后端测试"

run: ## 启动后端服务
	@python -m backend.run

build: ## 构建前端并嵌入后端静态目录
	cd frontend && npm install && npm run build
	rm -rf backend/static && cp -r frontend/dist backend/static

install: ## 安装所有依赖（Python + Node）
	pip install -r requirements.txt
	cd frontend && npm install

setup: install build ## 一键安装 + 构建（首次使用）
	@echo "✅ 完成！运行 'make run' 启动服务。"

test: ## 运行后端测试
	pytest -q
