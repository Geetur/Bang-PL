from lexer import Lexer
from expression_parser import ExpressionParser, ParserError
from control_flow_parser import ControlFlowParser
from semantic_analysis import SemanticAnalysis, SemanticError

def main():
    # 1) Lex & tokenize
    lexer = Lexer("input.txt")
    tokens = lexer.tokenizer()
    file = lexer.file                # source‐file lines for error reporting
    
    
    # 2) Split into logical lines
    expr_parser = ExpressionParser(tokens, file)
    expr_parser.split()              # populates expr_parser.post_split
    try:
        # 3) Build flat expression/control‐keywords stream
        all_expr_nodes = expr_parser.loading_into_algos()
        print(all_expr_nodes)
        
        
        # 4) Nest by control flow
        cf_parser = ControlFlowParser(file, all_expr_nodes)  
        block_nodes = cf_parser.blockenize()



        sem = SemanticAnalysis(file, block_nodes)
        sem.walk_program()


        # 5) Print out the fully nested AST
        for idx, node in enumerate(block_nodes, start=1):
            print(f"Node {idx}: {node!r}")

    except ParserError as pe:
        # nicely print parsing errors with location
        print(pe)
    except Exception as e:
        print(f"Unexpected error during parsing: {e}")

if __name__ == "__main__":
    main()