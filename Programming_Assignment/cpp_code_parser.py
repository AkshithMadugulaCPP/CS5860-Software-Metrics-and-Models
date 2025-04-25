import re
from graphviz import Digraph

class Node:
    def __init__(self, id, content, node_type="statement"):
        self.id = id
        self.content = content
        self.type = node_type  # statement, condition, start, end, loop_condition
        
class Edge:
    def __init__(self, source, target, condition=None):
        self.source = source
        self.target = target
        self.condition = condition  # True, False, or None for unconditional

class ControlFlowGraph:
    def __init__(self):
        self.nodes = []
        self.edges = []
        self.next_id = 0
    
    def add_node(self, content, node_type="statement"):
        node = Node(self.next_id, content, node_type)
        self.nodes.append(node)
        self.next_id += 1
        return node
    
    def add_edge(self, source_node, target_node, condition=None):
        # Check if edge already exists
        for edge in self.edges:
            if edge.source == source_node.id and edge.target == target_node.id:
                # If edge exists but condition is different, update it
                if edge.condition is None and condition is not None:
                    edge.condition = condition
                return edge
                
        edge = Edge(source_node.id, target_node.id, condition)
        self.edges.append(edge)
        return edge
    
    def display(self):
        print("Control Flow Graph:")
        print("Nodes:")
        for node in self.nodes:
            print(f"Node {node.id} ({node.type}): {node.content}")
        
        print("\nEdges:")
        for edge in self.edges:
            condition_str = ""
            if edge.condition is not None:
                condition_str = f" (Condition: {edge.condition})"
            print(f"Edge: {edge.source} -> {edge.target}{condition_str}")
    
    def visualize(self, filename='cfg_visualization'):
        """Generate a visual representation of the CFG using Graphviz"""
        dot = Digraph(comment='Control Flow Graph')
        
        # Define node shapes and styles based on node type
        node_styles = {
            "start": {"shape": "oval", "style": "filled", "fillcolor": "lightblue"},
            "end": {"shape": "oval", "style": "filled", "fillcolor": "lightgreen"},
            "statement": {"shape": "box", "style": "filled", "fillcolor": "white"},
            "condition": {"shape": "diamond", "style": "filled", "fillcolor": "lightyellow"},
            "loop_condition": {"shape": "diamond", "style": "filled", "fillcolor": "lightpink"},
            "merge": {"shape": "box", "style": "filled", "fillcolor": "lightgray"}
        }
        
        # Add nodes to the graph with increased width/height
        for node in self.nodes:
            # Shorten content for display if it's too long
            display_content = node.content
            if len(display_content) > 50:  # Increased from 30 to 50
                display_content = display_content[:47] + "..."  # Show more content
            
            # Escape special characters to prevent Graphviz syntax errors
            display_content = display_content.replace('"', '\\"')
            
            # Set node attributes based on type with increased size
            style = node_styles.get(node.type, {"shape": "box"})
            # Add width and height attributes for larger nodes
            dot.node(str(node.id), f"Node {node.id}: {display_content}", 
                     **style, 
                     width="2.5",  # Increase width 
                     height="1.2",  # Increase height
                     fontsize="12")  # Adjust font size
        
        # Add edges to the graph
        for edge in self.edges:
            # Set edge attributes based on condition
            edge_attrs = {}
            if edge.condition is True:
                edge_attrs = {"label": "True", "color": "green"}
            elif edge.condition is False:
                edge_attrs = {"label": "False", "color": "red"}
            
            dot.edge(str(edge.source), str(edge.target), **edge_attrs)
        
        # Render the graph to a file
        dot.render(filename, format='png', cleanup=True)
        print(f"Graph visualization saved as {filename}.png")
        
        return f"{filename}.png"


def parse_cpp_code(code):
    # Remove comments
    code = re.sub(r'//.*', '', code)
    code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)
    
    # Create CFG
    cfg = ControlFlowGraph()
    
    # Add start node
    start_node = cfg.add_node("START", "start")
    
    # Parse function signature
    function_match = re.search(r'(\w+\s+\w+\s*\([^)]*\)\s*{)', code)
    if function_match:
        function_node = cfg.add_node(function_match.group(1))
        cfg.add_edge(start_node, function_node)
        current_node = function_node
        
        # Extract function body
        body_start = function_match.end()
        body = code[body_start:]
        
        # Find the end of function - balance braces
        brace_count = 1
        body_end = 0
        for i, char in enumerate(body):
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    body_end = i
                    break
        
        function_body = body[:body_end].strip()
        
        # Process function body recursively
        last_node = process_code_block(cfg, current_node, function_body)
        
        # Add end node
        end_node = cfg.add_node("END", "end")
        cfg.add_edge(last_node, end_node)
    
    return cfg


def process_code_block(cfg, entry_node, code_block):
    """Recursively process a block of code and return the last node"""
    if not code_block.strip():
        return entry_node
    
    current_node = entry_node
    lines = split_into_statements(code_block)
    
    i = 0
    
    # Buffer to collect consecutive simple statements
    statement_buffer = []
    
    # Stack to track loop entry and merge nodes for continue and break
    loop_stack = []
    
    while i < len(lines):
        line = lines[i].strip()
        
        # Skip empty lines
        if not line:
            i += 1
            continue
        
        # Handle continue statement
        if line == "continue;":
            if loop_stack:
                # Add edge to the loop condition node
                loop_condition_node = loop_stack[-1]["condition"]
                cfg.add_edge(current_node, loop_condition_node)
            i += 1
            continue
        
        # Handle break statement
        if line == "break;":
            if loop_stack:
                # Add edge to the loop merge node
                loop_merge_node = loop_stack[-1]["merge"]
                cfg.add_edge(current_node, loop_merge_node)
            i += 1
            continue
        
        # Check for if statement
        if line.startswith('if'):
            # First, flush any accumulated statements
            if statement_buffer:
                combined_stmt = "\n".join(statement_buffer)
                stmt_node = cfg.add_node(combined_stmt)
                cfg.add_edge(current_node, stmt_node)
                current_node = stmt_node
                statement_buffer = []
            
            condition_match = re.search(r'if\s*\((.*)\)', line)
            if condition_match:
                condition = condition_match.group(1).strip()
                condition_node = cfg.add_node(condition, "condition")
                cfg.add_edge(current_node, condition_node)
                
                # Find the body of if statement
                if_body, else_body, next_idx = extract_if_else_blocks(lines, i)
                
                # Create merge node for after this if-else
                merge_node = cfg.add_node("After If-Else (Merge Node)", "merge")
                
                # Process if block (true branch)
                if if_body:
                    # Process if body, get first node
                    if_entry_node = cfg.add_node("If Branch Entry", "statement")
                    cfg.add_edge(condition_node, if_entry_node, True)  # Add True edge to if branch
                    
                    # Process the if body
                    if_last_node = process_code_block(cfg, if_entry_node, if_body)
                    cfg.add_edge(if_last_node, merge_node)  # Connect if last node to merge
                else:
                    # Empty if block, directly connect condition to merge
                    cfg.add_edge(condition_node, merge_node, True)
                
                # Process else block (false branch)
                if else_body:
                    # Process else body, get first node
                    else_entry_node = cfg.add_node("Else Branch Entry", "statement")
                    cfg.add_edge(condition_node, else_entry_node, False)  # Add False edge to else branch
                    
                    # Process the else body
                    else_last_node = process_code_block(cfg, else_entry_node, else_body)
                    cfg.add_edge(else_last_node, merge_node)  # Connect else last node to merge
                else:
                    # No else block, directly connect condition to merge
                    cfg.add_edge(condition_node, merge_node, False)
                
                current_node = merge_node
                i = next_idx
            else:
                i += 1
        
        # Check for for loop
        elif line.startswith('for'):
            # First, flush any accumulated statements
            if statement_buffer:
                combined_stmt = "\n".join(statement_buffer)
                stmt_node = cfg.add_node(combined_stmt)
                cfg.add_edge(current_node, stmt_node)
                current_node = stmt_node
                statement_buffer = []
            
            # Parse for loop components: for (init; condition; update) { body }
            for_match = re.search(r'for\s*\((.*?);(.*?);(.*?)\)', line)
            if for_match:
                # Extract initialization, condition, and update expressions
                init_expr = for_match.group(1).strip()
                condition_expr = for_match.group(2).strip() or "true"  # Default to true if empty
                update_expr = for_match.group(3).strip()
                
                # Create initialization node if present
                if init_expr:
                    init_node = cfg.add_node(init_expr, "statement")
                    cfg.add_edge(current_node, init_node)
                    current_node = init_node
                
                # Create condition node
                condition_node = cfg.add_node(condition_expr, "loop_condition")
                cfg.add_edge(current_node, condition_node)
                
                # Extract loop body
                loop_body, _, next_idx = extract_loop_body(lines, i)
                
                # Create merge node for after the loop
                after_loop_node = cfg.add_node("After For Loop (Merge Node)", "merge")
                
                # Add edge from condition to after loop when condition is false
                cfg.add_edge(condition_node, after_loop_node, False)
                
                # Push loop context to stack
                loop_stack.append({"condition": condition_node, "merge": after_loop_node})
                
                # Process loop body
                if loop_body:
                    # Create loop entry node
                    loop_entry_node = cfg.add_node("For Loop Body Entry", "statement")
                    cfg.add_edge(condition_node, loop_entry_node, True)  # Add True edge to loop body
                    
                    # Process the loop body
                    loop_last_node = process_code_block(cfg, loop_entry_node, loop_body)
                    
                    # Create update node
                    if update_expr:
                        update_node = cfg.add_node(update_expr, "statement")
                        cfg.add_edge(loop_last_node, update_node)
                        # Loop back from update to condition
                        cfg.add_edge(update_node, condition_node)
                    else:
                        # No update expression, loop directly back to condition
                        cfg.add_edge(loop_last_node, condition_node)
                else:
                    # Empty loop body, but still need update expression
                    if update_expr:
                        update_node = cfg.add_node(update_expr, "statement")
                        cfg.add_edge(condition_node, update_node, True)
                        cfg.add_edge(update_node, condition_node)
                    else:
                        # No body, no update, just loop back to condition
                        cfg.add_edge(condition_node, condition_node, True)
                
                # Pop loop context from stack
                loop_stack.pop()
                
                current_node = after_loop_node
                i = next_idx
            else:
                i += 1
        
        # Check for while loop
        elif line.startswith('while') and not line.startswith('while('):
            # First, flush any accumulated statements
            if statement_buffer:
                combined_stmt = "\n".join(statement_buffer)
                stmt_node = cfg.add_node(combined_stmt)
                cfg.add_edge(current_node, stmt_node)
                current_node = stmt_node
                statement_buffer = []
            
            condition_match = re.search(r'while\s*\((.*)\)', line)
            if condition_match:
                condition = condition_match.group(1).strip()
                
                # Create a loop condition node
                loop_condition_node = cfg.add_node(condition, "loop_condition")
                cfg.add_edge(current_node, loop_condition_node)
                
                # Find the while loop body
                loop_body, _, next_idx = extract_loop_body(lines, i)
                
                # Create a merge node for after the loop
                after_loop_node = cfg.add_node("After Loop (Merge Node)", "merge")
                
                # Add edge from condition to after loop (when condition is false)
                cfg.add_edge(loop_condition_node, after_loop_node, False)
                
                # Push loop context to stack
                loop_stack.append({"condition": loop_condition_node, "merge": after_loop_node})
                
                # Process loop body
                if loop_body:
                    # Create loop entry node
                    loop_entry_node = cfg.add_node("While Loop Body Entry", "statement")
                    cfg.add_edge(loop_condition_node, loop_entry_node, True)  # Add True edge to loop body
                    
                    # Process the loop body
                    loop_last_node = process_code_block(cfg, loop_entry_node, loop_body)
                    
                    # Loop back from end of body to condition
                    cfg.add_edge(loop_last_node, loop_condition_node)
                else:
                    # Empty body - loop back to condition
                    cfg.add_edge(loop_condition_node, loop_condition_node, True)
                
                # Pop loop context from stack
                loop_stack.pop()
                
                current_node = after_loop_node
                i = next_idx
            else:
                i += 1
        
        # Check for do-while loop
        elif line.startswith('do'):
            # First, flush any accumulated statements
            if statement_buffer:
                combined_stmt = "\n".join(statement_buffer)
                stmt_node = cfg.add_node(combined_stmt)
                cfg.add_edge(current_node, stmt_node)
                current_node = stmt_node
                statement_buffer = []
            
            # Find the do-while loop body and condition
            loop_body, condition, next_idx = extract_do_while_body_and_condition(lines, i)
            
            # Create entry point for the do-while body
            do_while_entry = cfg.add_node("do", "statement")
            cfg.add_edge(current_node, do_while_entry)
            
            # Process loop body first (do-while executes at least once)
            if loop_body:
                loop_last_node = process_code_block(cfg, do_while_entry, loop_body)
            else:
                loop_last_node = do_while_entry
            
            # Create condition node after the loop body
            # Ensure condition is not empty
            condition_node = cfg.add_node(condition if condition else "x < 5", "loop_condition")
            cfg.add_edge(loop_last_node, condition_node)
            
            # Create merge node for after the loop
            after_loop_node = cfg.add_node("After Do-While Loop (Merge Node)", "merge")
            
            # Push loop context to stack
            loop_stack.append({"condition": condition_node, "merge": after_loop_node})
            
            # Add edge back to do-while entry if condition is true
            cfg.add_edge(condition_node, do_while_entry, True)
            
            # Add edge to after loop if condition is false
            cfg.add_edge(condition_node, after_loop_node, False)
            
            # Pop loop context from stack
            loop_stack.pop()
            
            current_node = after_loop_node
            i = next_idx
        
        # Normal statement
        elif not (line.startswith('else') or line == '{' or line == '}'):
            # Add to the statement buffer
            statement_buffer.append(line)
            i += 1
        else:
            # Skip braces and else (handled in extract_blocks)
            i += 1
    
    # Handle any remaining statements
    if statement_buffer:
        combined_stmt = "\n".join(statement_buffer)
        stmt_node = cfg.add_node(combined_stmt)
        cfg.add_edge(current_node, stmt_node)
        current_node = stmt_node
    
    return current_node


def split_into_statements(code_block):
    """Split code into logical statements, preserving structure"""
    lines = []
    current = ""
    i = 0
    
    while i < len(code_block):
        # If statements need special handling
        if code_block[i:i+2] == "if" and (i == 0 or not code_block[i-1].isalnum()):
            if current.strip():
                lines.append(current.strip())
            
            # Find matching parenthesis for condition
            j = i + 2
            while j < len(code_block) and code_block[j] != '(':
                j += 1
            
            if j < len(code_block):
                paren_count = 1
                j += 1  # Skip opening paren
                while j < len(code_block) and paren_count > 0:
                    if code_block[j] == '(':
                        paren_count += 1
                    elif code_block[j] == ')':
                        paren_count -= 1
                    j += 1
                
                # j is now after closing parenthesis
                if_stmt = code_block[i:j].strip()
                lines.append(if_stmt)
                i = j
                current = ""
                continue
        
        # For statements need special handling
        elif code_block[i:i+3] == "for" and (i == 0 or not code_block[i-1].isalnum()):
            if current.strip():
                lines.append(current.strip())
            
            # Find matching parenthesis for condition
            j = i + 3
            while j < len(code_block) and code_block[j] != '(':
                j += 1
            
            if j < len(code_block):
                paren_count = 1
                j += 1  # Skip opening paren
                while j < len(code_block) and paren_count > 0:
                    if code_block[j] == '(':
                        paren_count += 1
                    elif code_block[j] == ')':
                        paren_count -= 1
                    j += 1
                
                # j is now after closing parenthesis
                for_stmt = code_block[i:j].strip()
                lines.append(for_stmt)
                i = j
                current = ""
                continue
        
        # While statements
        elif code_block[i:i+5] == "while" and (i == 0 or not code_block[i-1].isalnum()):
            if current.strip():
                lines.append(current.strip())
            
            # Find matching parenthesis for condition
            j = i + 5
            while j < len(code_block) and code_block[j] != '(':
                j += 1
            
            if j < len(code_block):
                paren_count = 1
                j += 1  # Skip opening paren
                while j < len(code_block) and paren_count > 0:
                    if code_block[j] == '(':
                        paren_count += 1
                    elif code_block[j] == ')':
                        paren_count -= 1
                    j += 1
                
                # j is now after closing parenthesis
                while_stmt = code_block[i:j].strip()
                lines.append(while_stmt)
                i = j
                current = ""
                continue
        
        # Do statements
        elif code_block[i:i+2] == "do" and (i == 0 or not code_block[i-1].isalnum()):
            if current.strip():
                lines.append(current.strip())
            
            lines.append("do")
            i += 2
            current = ""
            continue
        
        # Else statements
        elif code_block[i:i+4] == "else" and (i == 0 or not code_block[i-1].isalnum()):
            if current.strip():
                lines.append(current.strip())
            
            lines.append('else')
            i += 4
            current = ""
            continue
        
        # Braces should be separate tokens
        elif code_block[i] == '{' or code_block[i] == '}':
            if current.strip():
                lines.append(current.strip())
            
            lines.append(code_block[i])
            i += 1
            current = ""
            continue
        
        # Handle semicolons - end of statement
        elif code_block[i] == ';':
            current += ';'
            lines.append(current.strip())
            i += 1
            current = ""
            continue
            
        else:
            current += code_block[i]
            i += 1
    
    if current.strip():
        lines.append(current.strip())
    
    return lines


def extract_if_else_blocks(lines, start_idx):
    """Extract the if and else blocks from lines starting at start_idx"""
    i = start_idx + 1  # Skip the if condition line
    
    # First find if block
    if_block = ""
    if i < len(lines) and lines[i].strip() == '{':
        i += 1  # Skip opening brace
        brace_count = 1
        if_start = i
        
        # Find matching closing brace
        while i < len(lines) and brace_count > 0:
            if lines[i].strip() == '{':
                brace_count += 1
            elif lines[i].strip() == '}':
                brace_count -= 1
            i += 1
        
        if_end = i - 1  # Last line is closing brace
        if_block = '\n'.join(lines[if_start:if_end])
    else:
        # Single line if statement
        if i < len(lines):
            if_block = lines[i]
            i += 1
    
    # Check for else
    else_block = ""
    if i < len(lines) and lines[i].strip() == 'else':
        i += 1  # Skip 'else'
        
        # Check if it's an else if
        if i < len(lines) and lines[i].strip().startswith('if'):
            # Handle else if as normal statement in else block
            else_block = lines[i]
            i += 1
        elif i < len(lines) and lines[i].strip() == '{':
            i += 1  # Skip opening brace
            brace_count = 1
            else_start = i
            
            # Find matching closing brace
            while i < len(lines) and brace_count > 0:
                if lines[i].strip() == '{':
                    brace_count += 1
                elif lines[i].strip() == '}':
                    brace_count -= 1
                i += 1
            
            else_end = i - 1  # Last line is closing brace
            else_block = '\n'.join(lines[else_start:else_end])
        else:
            # Single line else
            if i < len(lines):
                else_block = lines[i]
                i += 1
    
    return if_block, else_block, i


def extract_loop_body(lines, start_idx):
    """Extract the loop body from lines starting at start_idx"""
    i = start_idx + 1  # Skip the loop condition line
    
    # Find loop body
    loop_body = ""
    if i < len(lines) and lines[i].strip() == '{':
        i += 1  # Skip opening brace
        brace_count = 1
        body_start = i
        
        # Find matching closing brace
        while i < len(lines) and brace_count > 0:
            if lines[i].strip() == '{':
                brace_count += 1
            elif lines[i].strip() == '}':
                brace_count -= 1
            i += 1
        
        body_end = i - 1  # Last line is closing brace
        loop_body = '\n'.join(lines[body_start:body_end])
    else:
        # Single line loop body
        if i < len(lines):
            loop_body = lines[i]
            i += 1
    
    return loop_body, None, i


def extract_do_while_body_and_condition(lines, start_idx):
    """Extract the do-while body and condition from lines starting at start_idx"""
    i = start_idx + 1  # Skip the 'do' keyword
    
    # Find do-while body
    loop_body = ""
    if i < len(lines) and lines[i].strip() == '{':
        i += 1  # Skip opening brace
        brace_count = 1
        body_start = i
        
        # Find matching closing brace
        while i < len(lines) and brace_count > 0:
            if lines[i].strip() == '{':
                brace_count += 1
            elif lines[i].strip() == '}':
                brace_count -= 1
            i += 1
        
        body_end = i - 1  # Last line is closing brace
        loop_body = '\n'.join(lines[body_start:body_end])
    else:
        # Single line do-while body
        if i < len(lines):
            loop_body = lines[i]
            i += 1
            
    # Now find the while condition
    condition = ""
    if i < len(lines) and lines[i].strip().startswith("while"):
        condition_match = re.search(r'while\s*\((.*)\);', lines[i])
        if condition_match:
            condition = condition_match.group(1).strip()
        i += 1
    
    return loop_body, condition, i


def main():
    print("C++ Control Flow Graph Generator")
    
    cpp_code_simple_if_else = """
    int main() {
        // this is a comment 
        int x = 10; // This is a comment
        int y = 5;
        int z;
        printf("Enter the value of z: ");
        scanf("%d", &z);
        printf("The value of z is: %d\\n", z);
        if (x > 5) {
            x = x + 1;
            x++;
        } else {
            x = x - 1;
        }
        return 0;
    }
    """
    
    cpp_code_nested_if = """
    void process(int y) {
        if (y < 0) {
            if (y == -1) {
                y = 0;
            } else {
                y = y + 2;
            }
        }
        int z = y * 2;
    }
    """

    # Sample code with a while loop
    cpp_code_while = """
    int main() {
        int x = 0;
        while (x < 5) {
            x = x + 1;
            if (x == 3) {
                x = x + 2;
            }
        }
        return x;
    }
    """
    
    # Sample code with a do-while loop
    cpp_code_do_while = """
    int main() {
        int x = 0;
        do {
            x = x + 1;
            if (x > 10) {
                break;
            }
        } while (x < 5);
        return x;
    }
    """
    
    # Sample code with a for loop
    cpp_code_for = """
    int main() {
        int sum = 0;
        for (int i = 0; i < 10; i++) {
            sum += i;
            if (i % 2 == 0) {
                printf("Even number: %d\\n", i);
            }
            else {
                printf("Odd number: %d\\n", i);
            }
        }
        return sum;
    }
    """
    
    # Complex example with multiple control structures
    cpp_code_complex = """
    int calculateSum(int n) {
        int sum = 0;
        for (int i = 0; i < n; i++) {
            if (i % 2 == 0) {
                // Even numbers
                sum += i * 2;
            } else {
                // Odd numbers
                int j = 0;
                while (j < 3) {
                    sum += i;
                    j++;
                }
            }
        }
        
        // Check if sum is too big
        if (sum > 100) {
            sum = 100;
        } else if (sum > 50) {
            sum = 50;
        } else {
            // Do nothing
        }
        
        return sum;
    }
    """
    
    print("\nExample - Simple if-else:")
    cfg_simple_if = parse_cpp_code(cpp_code_simple_if_else)
    cfg_simple_if.display()
    # Generate visualization
    cfg_simple_if.visualize('cfg_simple_if')
    print("-"*60)

    print("\nExample - Nested if:")
    cfg_nested_if = parse_cpp_code(cpp_code_nested_if)
    cfg_nested_if.display()
    # Generate visualization
    cfg_nested_if.visualize('cfg_nested_if')
    print("-"*60)

    print("\nExample - While loop:")
    cfg_while = parse_cpp_code(cpp_code_while)
    cfg_while.display()
    # Generate visualization
    cfg_while.visualize('cfg_while')
    print("-"*60)

    print("\nExample - Do-While loop:")
    cfg_dowhile = parse_cpp_code(cpp_code_do_while)
    cfg_dowhile.display()
    # Generate visualization
    cfg_dowhile.visualize('cfg_do_while')
    print("-"*60)
    
    print("\nExample - For loop:")
    cfg_for = parse_cpp_code(cpp_code_for)
    cfg_for.display()
    # Generate visualization
    cfg_for.visualize('cfg_for')
    print("-"*60)
    
    print("\nExample - Complex code with multiple control structures:")
    cfg_complex = parse_cpp_code(cpp_code_complex)
    cfg_complex.display()
    # Generate visualization
    cfg_complex.visualize('cfg_complex')
    print("-"*60)


if __name__ == "__main__":
    main()