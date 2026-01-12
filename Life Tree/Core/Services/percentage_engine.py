def _get_subtree_mass(node):
    """
    Returns (solved_count, total_count) for the subtree starting at node.
    Each node counts as 1 unit of 'mass'.
    If the node itself is 'solved', its entire subtree is considered 100% complete.
    """
    children = getattr(node, 'children', [])
    
    # Base count for the node itself
    total_count = 1
    
    # If the node itself is solved, the entire subtree mass (current + recursive children) 
    # is considered solved. We still need the total count for the percentage base.
    node_is_solved = getattr(node, 'status', 'neutral') == 'solved'
    
    recursive_solved = 0
    recursive_total = 0
    
    for child in children:
        c_solved, c_total = _get_subtree_mass(child)
        recursive_solved += c_solved
        recursive_total += c_total
    
    final_total = total_count + recursive_total
    
    if node_is_solved:
        return final_total, final_total
        
    return recursive_solved, final_total

def calculate_node_percentage(node):
    """
    Calculates percentage based on Subtree Mass Normalization:
    Percentage = (Total Solved Nodes in Subtree) / (Total Nodes in Subtree) * 100.
    """
    solved, total = _get_subtree_mass(node)
    
    if total == 0:
        return 0.0
        
    return (solved / total) * 100.0
