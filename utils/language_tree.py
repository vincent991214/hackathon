import json
import os
from pathlib import Path
from tree_sitter import Language, Parser
from tree_sitter_languages import get_parser # 这个库简化了语言解析器的获取
from tools.config import ToolConfig
from utils.codebase_rglob import safe_rglob

TREE_SITTER_LANGUAGE_MAP = ToolConfig().TREE_SITTER_MAP

def extract_node_info(node, source_code):
    """Extract information for a single node."""
    node_text = source_code[node.start_byte : node.end_byte].decode('utf8', errors='replace')
    
    node_info = {
        "type": node.type,
        "start_line": node.start_point[0],
        "start_col": node.start_point[1],
        "end_line": node.end_point[0],
        "end_col": node.end_point[1],
        "text": node_text.strip() if len(node_text.strip()) < 200 else node_text[:200].strip() + "...",
        "children": []
    }
    
    # If it's a leaf node, we can add additional info
    if node.child_count == 0:
        node_info["is_leaf"] = True
        node_info["content"] = repr(node_text)
    else:
        node_info["is_leaf"] = False
    
    return node_info


def build_structured_tree(node, source_code):
    """Build a structured representation of the syntax tree."""
    node_info = extract_node_info(node, source_code)
    
    # Recursively process children
    for child in node.children:
        child_info = build_structured_tree(child, source_code)
        node_info["children"].append(child_info)
    
    return node_info


def format_function_info(func_node, source_code):
    """Extract function information."""
    func_text = source_code[func_node.start_byte : func_node.end_byte].decode('utf8', errors='replace')
    
    # Attempt to find the function name
    name_node = None
    for child in func_node.children:
        if child.type in ['identifier', 'function_name']:
            name_node = child
            break
    
    func_name = ""
    if name_node:
        func_name = source_code[name_node.start_byte : name_node.end_byte].decode('utf8', errors='replace')
    
    return {
        "function_name": func_name,
        "type": func_node.type,
        "signature": func_text.split('\n')[0].strip() if '\n' in func_text else func_text.strip(),
        "location": f"[{func_node.start_point[0]}:{func_node.start_point[1]} - {func_node.end_point[0]}:{func_node.end_point[1]}]",
        "full_text": func_text
    }

def find_functions_in_tree(node, functions_list, source_code):
    """Find all function definitions in the syntax tree."""
    # Distinguish function definition nodes based on common types
    function_types = [
        'function_definition', 'method_declaration', 'function_declaration',
        'lambda_expression', 'arrow_function', 'constructor_declaration'
    ]
    
    if node.type in function_types:
        func_info = format_function_info(node, source_code)
        functions_list.append(func_info)
    
    # Traverse children
    for child in node.children:
        find_functions_in_tree(child, functions_list, source_code)

def find_imports_and_declarations(node, imports_list, declarations_list, source_code):
    """Find import statements and declarations in the syntax tree."""
    import_types = ['import_statement', 'import_declaration', 'include_preproc']
    declaration_types = [
        'class_declaration', 'interface_declaration', 'struct_declaration',
        'enum_declaration', 'variable_declaration', 'field_declaration'
    ]
    
    if node.type in import_types:
        import_text = source_code[node.start_byte : node.end_byte].decode('utf8', errors='replace')
        imports_list.append({
            "type": node.type,
            "content": import_text.strip(),
            "location": f"[{node.start_point[0]}:{node.start_point[1]} - {node.end_point[0]}:{node.end_point[1]}]"
        })
    
    if node.type in declaration_types:
        decl_text = source_code[node.start_byte : node.end_byte].decode('utf8', errors='replace')
        declarations_list.append({
            "type": node.type,
            "name": extract_declaration_name(node, source_code),
            "content": decl_text.strip(),
            "location": f"[{node.start_point[0]}:{node.start_point[1]} - {node.end_point[0]}:{node.end_point[1]}]"
        })
    
    # Traverse children
    for child in node.children:
        find_imports_and_declarations(child, imports_list, declarations_list, source_code)

def extract_declaration_name(node, source_code):
    """Extract the name of a declaration node."""
    for child in node.children:
        if child.type in ['identifier', 'type_identifier', 'field_identifier']:
            return source_code[child.start_byte : child.end_byte].decode('utf8', errors='replace')
    return "unknown"


def generate_llm_friendly_summary(file_path, language_name, structured_tree, functions, imports, declarations):
    """Generate a summary suitable for LLM consumption."""
    summary = {
        "file_path": str(file_path),
        "language": language_name,
        "summary": {
            "total_functions": len(functions),
            "total_imports": len(imports),
            "total_classes_or_structures": len([d for d in declarations if d['type'] in ['class_declaration', 'interface_declaration', 'struct_declaration']])
        },
        "functions": functions,
        "imports": imports,
        "declarations": declarations,
        "structure_overview": structured_tree
    }
    
    return summary

def parse_project_for_llm(project_path):
    """Parse all supported code files in the given project directory and generate LLM-friendly summaries."""
    
    # Collect all supported files
    supported_files = []
    for file_path in safe_rglob(Path(project_path)):
        if file_path.is_file():
            language_name = get_language_for_file(file_path)
            if language_name:
                 full_path = file_path
                 supported_files.append((full_path, language_name))
    
    print(f"Found {len(supported_files)} files to parse.")
    
    all_results = []

    for file_path, language_name in supported_files:
        print(f"\n--- Parsing File: {file_path} (Language: {language_name}) ---")
        
        # Try to get the parser for the language
        try:
            parser = get_parser(language_name)
        except ValueError as e:
            print(f"  Error: Could not load parser for '{language_name}'. Is it installed? Details: {e}")
            continue
        except Exception as e:
            print(f"  Unexpected error loading parser for '{language_name}': {e}")
            continue

        try:
            with open(file_path, 'rb') as f:
                source_code = f.read()

            # parse the source code and obtain the syntax tree
            tree = parser.parse(source_code)

            # get structured tree representation
            structured_tree = build_structured_tree(tree.root_node, source_code)

            # get function definitions
            functions = []
            find_functions_in_tree(tree.root_node, functions, source_code)

            # get imports and declarations
            imports = []
            declarations = []
            find_imports_and_declarations(tree.root_node, imports, declarations, source_code)

            # generate LLM-friendly summary
            llm_summary = generate_llm_friendly_summary(
                file_path, language_name, structured_tree, functions, imports, declarations
            )
            
            all_results.append(llm_summary)

        except Exception as e:
            print(f"  Error parsing {file_path}: {e}")
    
    return all_results

def get_language_for_file(file_path):
    """
    Return the corresponding tree-sitter language name based on file extension.
    """

    _, ext = os.path.splitext(str(file_path).lower())
    return TREE_SITTER_LANGUAGE_MAP.get(ext, None)



project_directory = r"C:\Users\zliu71\Documents\BagMessageDistribution"
results = parse_project_for_llm(project_directory)

print(json.dumps(results, indent=2))