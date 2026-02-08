from tools.config import ToolConfig

def safe_rglob(root_path, pattern='*'):
    """在遍历前就排除指定目录"""
    def _recursive_search(current_path, pat):
        try:
            for item in current_path.iterdir():
                if item.name in ToolConfig().IGNORED_DIRS:
                    continue 
                
                if item.is_file():
                    if item.match(pat):
                        yield item
                elif item.is_dir():
                    yield from _recursive_search(item, pat)
        except PermissionError:
            pass  # 忽略权限错误
    
    return _recursive_search(root_path, pattern)