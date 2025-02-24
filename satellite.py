class TreeNode:
    def __init__(self, value):
        self.value = value
        self.left = None
        self.right = None

def validate_traversals(preorder, inorder):
    """Validate the traversal inputs."""
    if len(preorder) != len(inorder):
        raise ValueError("traversals must have the same length")
    
    # Convert to sets once for both uniqueness and equality checks
    preorder_set = set(preorder)
    inorder_set = set(inorder)
    
    if len(preorder) != len(preorder_set):
        raise ValueError("traversals must contain unique items")
        
    if preorder_set != inorder_set:
        raise ValueError("traversals must have the same elements")

def build_tree_helper(preorder, inorder, pre_start, pre_end, in_start, in_end):
    """Helper function that builds tree using index ranges instead of slicing."""
    if pre_start > pre_end or in_start > in_end:
        return None
        
    # Root is always the first element of preorder section
    root = TreeNode(preorder[pre_start])
    
    # Find root in inorder traversal
    root_idx = inorder.index(preorder[pre_start])
    left_size = root_idx - in_start
    
    # Recursively build left and right subtrees
    root.left = build_tree_helper(
        preorder, inorder,
        pre_start + 1, pre_start + left_size,
        in_start, root_idx - 1
    )
    
    root.right = build_tree_helper(
        preorder, inorder,
        pre_start + left_size + 1, pre_end,
        root_idx + 1, in_end
    )
    
    return root

def tree_from_traversals(preorder, inorder):
    """Reconstruct binary tree from its preorder and inorder traversals."""
    # Validate inputs first
    validate_traversals(preorder, inorder)
    
    # Build the tree using index ranges
    return build_tree_helper(
        preorder, inorder,
        0, len(preorder) - 1,
        0, len(inorder) - 1
    )
