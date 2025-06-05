{% raw %}
#!/bin/bash

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检测操作系统
detect_os() {
    if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]] || [[ "$OS" == "Windows_NT" ]]; then
        echo "windows"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    else
        echo "linux"
    fi
}

# 检测 uv 是否安装
check_uv_installed() {
    if command -v uv &> /dev/null; then
        log_success "uv 已安装，版本: $(uv --version)"
        return 0
    else
        log_warning "uv 未安装"
        return 1
    fi
}

# 安装 uv
install_uv() {
    log_info "正在安装 uv..."
    
    local os=$(detect_os)
    case $os in
        "windows")
            if command -v pip &> /dev/null; then
                pip install uv
            else
                log_error "pip 未找到，请先安装 Python 和 pip"
                exit 1
            fi
            ;;
        "macos"|"linux")
            if command -v pip &> /dev/null; then
                pip install uv
            elif command -v pip3 &> /dev/null; then
                pip3 install uv
            else
                log_error "pip 未找到，请先安装 Python 和 pip"
                exit 1
            fi
            ;;
    esac
    
    if check_uv_installed; then
        log_success "uv 安装成功"
    else
        log_error "uv 安装失败"
        exit 1
    fi
}

# 检查依赖文件是否存在
check_requirements_files() {
    local missing_files=()
    
    if [[ ! -f "requirements.txt" ]]; then
        missing_files+=("requirements.txt")
    fi
    
    if [[ ! -f "requirements-dev.txt" ]]; then
        missing_files+=("requirements-dev.txt")
    fi
    
    if [[ ${#missing_files[@]} -gt 0 ]]; then
        log_error "缺少依赖文件: ${missing_files[*]}"
        return 1
    fi
    
    return 0
}

# 检查虚拟环境是否存在
check_venv_exists() {
    if [[ -d ".venv" ]]; then
        log_info "虚拟环境已存在"
        return 0
    else
        log_info "虚拟环境不存在，将创建新的虚拟环境"
        return 1
    fi
}

# 检查依赖是否已安装
check_dependencies_installed() {
    if [[ -f ".venv/pyvenv.cfg" ]] && ([[ -d ".venv/lib" ]] || [[ -d ".venv/Lib" ]]); then
        local site_packages_dir
        site_packages_dir=$(find .venv -type d -name "site-packages" | head -n 1)
        if [[ -n "$site_packages_dir" ]] && [[ $(ls -A "$site_packages_dir" | wc -l) -gt 2 ]]; then
            log_info "检测到已安装的依赖包"
            return 0
        fi
    fi
    return 1
}

# 安装依赖
install_dependencies() {
    log_info "正在安装主依赖..."
    if uv add -r requirements.txt; then
        log_success "主依赖安装成功"
    else
        log_error "主依赖安装失败"
        exit 1
    fi
    
    log_info "正在安装开发依赖..."
    if uv add -r requirements-dev.txt --group dev; then
        log_success "开发依赖安装成功"
    else
        log_error "开发依赖安装失败"
        exit 1
    fi

    log_info "生成编译依赖..."
    if uv pip compile pyproject.toml -o uv.linux.lock; then
        log_success "编译依赖生成成功"
    else
        log_error "编译依赖生成失败"
        exit 1
    fi
    
}

# 激活虚拟环境
activate_venv() {
    local os=$(detect_os)
    case $os in
        "windows")
            if [[ -f ".venv/Scripts/activate" ]]; then
                log_info "激活虚拟环境 (Windows)"
                source .venv/Scripts/activate
            elif [[ -f ".venv/Scripts/Activate.ps1" ]]; then
                log_warning "检测到 PowerShell 脚本，请在 PowerShell 中运行: .venv\\Scripts\\Activate.ps1"
            else
                log_error "虚拟环境激活脚本未找到"
                exit 1
            fi
            ;;
        "macos"|"linux")
            if [[ -f ".venv/bin/activate" ]]; then
                log_info "激活虚拟环境 (Unix)"
                source .venv/bin/activate
            else
                log_error "虚拟环境激活脚本未找到"
                exit 1
            fi
            ;;
    esac
}

# 启动应用
start_app() {
    log_info "正在启动应用..."
    log_info "服务将运行在: http://0.0.0.0:8000"
    log_info "按 Ctrl+C 停止服务"
    
    if command -v uvicorn &> /dev/null; then
        uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
    else
        log_error "uvicorn 未找到，请检查依赖安装"
        exit 1
    fi
}

# 主函数
main() {
    log_info "开始启动应用..."
    
    # 检查 uv 是否安装
    if ! check_uv_installed; then
        read -p "是否安装 uv? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            install_uv
        else
            log_error "uv 是必需的，退出"
            exit 1
        fi
    fi
    
    # 检查依赖文件
    if ! check_requirements_files; then
        exit 1
    fi
    
    # 检查并安装依赖
    if ! check_dependencies_installed; then
        log_info "需要安装依赖"
        install_dependencies
    else
        log_info "依赖已安装，跳过安装步骤"
    fi
    
    # 激活虚拟环境
    activate_venv
    
    # 启动应用
    start_app
}

# 脚本入口
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
{% endraw %}