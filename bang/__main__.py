from bang.lexing.lexer import Lexer
from bang.parsing.expression_parser import ExpressionParser, ParserError
from bang.parsing.control_flow_parser import ControlFlowParser
from bang.semantic.semantic_analysis import SemanticAnalysis, SemanticError
from bang.runtime.evaluator import Evaluator, EvaluatorError

def main():
    # 1) Lex & tokenize
    lexer = Lexer("examples\input2.bang")
    tokens = lexer.tokenizer()
    file = lexer.file                # source‐file lines for error reporting
    
    
    # 2) Split into logical lines
    expr_parser = ExpressionParser(tokens, file)
    expr_parser.split()              # populates expr_parser.post_split
    try:
        # 3) Build flat expression/control‐keywords stream
        all_expr_nodes = expr_parser.loading_into_algos()
        
        # 4) Nest by control flow
        cf_parser = ControlFlowParser(file, all_expr_nodes)  
        block_nodes = cf_parser.blockenize()
        
        sem = SemanticAnalysis(file, block_nodes)
        sem.walk_program()

        # 5) Print out the fully nested AST
        ev  = Evaluator(file, block_nodes)
        ev.eval_program()

    except (ParserError, SemanticError, EvaluatorError) as err:
        print(err)

if __name__ == "__main__":
    main()