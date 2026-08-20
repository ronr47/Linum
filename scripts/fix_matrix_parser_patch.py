"""
Reference patch for Matrix Literal Parsing and Semantic Diagnostic Error Propagation.
Integrate this logic into your Linum parser and semantic checker to resolve:
'error[syntax]: Parser Error: Unexpected token in expression: TokenType.LBRACKET'
"""

class TokenType:
    LBRACKET = "LBRACKET"
    RBRACKET = "RBRACKET"
    COMMA = "COMMA"
    IDENTIFIER = "IDENTIFIER"
    NUMBER = "NUMBER"
    EOF = "EOF"

class DiagnosticError(Exception):
    pass

class ASTNode:
    pass

class MatrixLiteral(ASTNode):
    def __init__(self, rows):
        self.rows = rows  # List[List[ASTNode]]

    def __repr__(self):
        return f"MatrixLiteral({self.rows})"

# ============================================================================
# PARSER EXTENSION
# ============================================================================

def parse_primary_expression(parser):
    """
    Ensure TokenType.LBRACKET routes to matrix/array parsing rather than
    raising an unexpected token syntax error.
    """
    if parser.match(TokenType.LBRACKET):
        return parse_matrix_or_list_literal(parser)
    
    # Handle other primaries (identifiers, literals, etc.)
    return parser.parse_base_primary()

def parse_matrix_or_list_literal(parser):
    """
    Parses nested bracket notation: [[1, 2], [3, 4]]
    """
    rows = []
    
    if not parser.check(TokenType.RBRACKET):
        # Parse first element/row
        first_elem = parser.parse_expression()
        
        # Check if 2D matrix literal or 1D list
        if isinstance(first_elem, list) or parser.match(TokenType.COMMA):
            rows.append(first_elem)
            while parser.match(TokenType.COMMA):
                rows.append(parser.parse_expression())
        else:
            rows.append(first_elem)

    parser.consume(TokenType.RBRACKET, "Expected ']' at end of matrix literal")
    return MatrixLiteral(rows=rows)

# ============================================================================
# SEMANTIC CHECKER & ERROR PROPAGATION
# ============================================================================

def evaluate_matrix_multiplication(mat_a_shape, mat_b_shape):
    """
    Validates (M x K) * (K x N) dimensions.
    Raises DiagnosticError matching test regex if dimensions mismatch.
    """
    rows_a, cols_a = mat_a_shape
    rows_b, cols_b = mat_b_shape
    
    if cols_a != rows_b:
        raise DiagnosticError(
            f"matrix multiplication dimension mismatch: cannot multiply ({rows_a}x{cols_a}) by ({rows_b}x{cols_b})"
        )
    return (rows_a, cols_b)

def evaluate_determinant(mat_shape):
    """
    Validates square matrix requirement for determinant calculation.
    Raises DiagnosticError matching test regex if non-square.
    """
    rows, cols = mat_shape
    if rows != cols:
        raise DiagnosticError(
            f"det expects a square matrix: received ({rows}x{cols})"
        )
    return True
