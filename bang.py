from collections import deque
######################################################################
# GLOBALS
######################################################################
#LANGUAGE CONSTRUCTS
TKEYWORD = "KEYWORD"
TIDENTIFIER = "IDENTIFIER"
#LANGUAGE CONSTRUCTS

#MISC OPERATORS
TENDLINE = "ENDLINE"
#MISC OPERATORS

#ASSIGNMENT
TASSIGN = "ASSIGN"
#ASSIGNMENT

#values
TFLOAT = "FLOAT"
TINT = "INT"
TBOOL = "BOOL"
TARRAY = "ARRAY"
#values

#LOGICAL OPERATORS
TGREATERTHAN = "GREATERTHAN"
TGREATERTHANEQUAL = "GREATERTHANEQUAL"
TLESSTHAN = "LESSTHAN"
TLESSTHANEQUAL = "LESSTHANEQUAL"
TEQUAL = "EQUAL"
TNOTEQUAL = "NOTEQUAL"
TAND = "AND"
TOR = "OR"
TNOT = "NOT"

#LOGICAL OPERATORS

#BINARY OPERATORS
TPLUS = "PLUS"
TMINUS = "MINUS"
TMUL = "MUL"                     # every token that can possibly exist
TDIV = "DIV"
TEXPO = "EXPO"
TUNARYMINUS = "UNARYMINUS"
TUNARYPLUS = "UNARYPLUS"
#BINARY OPERATORS

#BRACKETS
TLPAREN = "LPAREN"
TRPAREN = "RPAREN"
TLBRACKET = "LBRACKET"
TRBRACKET = "TRBRACKET"
#BRACKETS

#KEYWORDS
TIF = "if"
TELIF = "elif"
TELSE = "else"
TENDIF = "endif"
TWHILE = "while"
TENDW = "endw"
TFOR = "for"
TENDF = "endf"
TCOMMA = "COMMA"


keywords = (TIF, TELIF, TELSE, TENDIF, TWHILE, TENDW, TFOR, TENDF)
#KEYWORDS


identifiers = {
                                  # user-declared/initalizaed variables will be stored here; any variables not in here were not declared/initalized
}


symbToTkn = {
    "+": TPLUS,
    "-": TMINUS,
    "=": TASSIGN,
    "*": TMUL,                   # map of symbols and their respective tokens (purpose is for brevity and organization)
    "/": TDIV,
    "p": TUNARYPLUS,
    "m": TUNARYMINUS,
    "(": TLPAREN,
    "[": TLBRACKET,
    "]": TRBRACKET,
    ")": TRPAREN,
    "^": TEXPO,
    ">": TGREATERTHAN,
    ">=": TGREATERTHANEQUAL,
    "<": TLESSTHAN,
    "<=": TLESSTHANEQUAL,
    "==": TEQUAL,
    "!=": TNOTEQUAL,
    "&&": TAND,
    "||": TOR,
    "!": TNOT,
    "\n": TENDLINE,
    ",": TCOMMA
}

tokenPositions, tokenPositionsForInterpreter = [], []              # tuple of (token start idx, token end idx, row where token exist)

errorIdxMapInterpreter = []

lineCopies,lineCopiesForInterpreter = [""], {}               # copies of each line of source code
correspondingEmptyLines = []

endifsEncountered, emptyLinesEncountered = 0, 0
######################################################################
# ERROR
######################################################################

def error(message, tokenPos, lineNum):
    errorArrows = ""

    try:
        if len(lineNum) == 2:
            startOfError, endOfError, errorRowIdx = tokenPos[0], tokenPos[1], tokenPos[2]
            errorLine = lineCopiesForInterpreter[errorRowIdx][0]
            errorRowIdx += lineCopiesForInterpreter[errorRowIdx][1] + 1
    except TypeError:
        if lineNum == -1:                                                                                                                              
            startOfError, endOfError, errorRowIdx = tokenPositions[tokenPos][0], tokenPositions[tokenPos][1], tokenPositions[tokenPos][2]
        else:
            startOfError, endOfError, errorRowIdx = tokenPositions[lineNum][tokenPos][0], tokenPositions[lineNum][tokenPos][1], tokenPositions[lineNum][tokenPos][2]                                                                                                              
        errorLine = lineCopies[errorRowIdx]
        if correspondingEmptyLines:
            if len(correspondingEmptyLines) > errorRowIdx:
                errorRowIdx += correspondingEmptyLines[errorRowIdx]    
            else:
                errorRowIdx += correspondingEmptyLines[-1]
            errorRowIdx += 1

    while len(errorArrows) != len(errorLine):                                                                                     
        if len(errorArrows) >= startOfError and len(errorArrows) <= endOfError:
            errorArrows += "^"
        else:
            errorArrows += " "   
                            
    return f"""                               
    Error at line {errorRowIdx}, char {startOfError}-{endOfError} 
    {errorLine}
    {errorArrows}
    {message}
    """

###################################################################### #REMOVE EMPTY AT END OF COPY LINE
# Lexer
######################################################################        # MUST FIND A WAY TO MAKE UNARY TRY AND REMOVE THE 1 * 


def lexer(text):
    
    idx, row, col = 0, 0, 0


    def lexLinesWithPosition(tokens):
        import pprint
        global tokenPositions, tokenPositionsForInterpreter
        currBlock, blocks = [], []
        currPosition, positions = [], []
        positionsForInterpreter = []
        for idx, i in enumerate(tokens):
            if i[0] == TENDLINE:
                if currBlock:
                    blocks.append(currBlock)
                    positions.append(currPosition)
                    if currBlock[-1][-1] not in ["endif", "endw", "endf"]:
                        interpreterCurrPosition = []
                        for i in currPosition:
                            interpreterCurrPosition.append((i[0], i[1], len(positionsForInterpreter)))
                        positionsForInterpreter.append(interpreterCurrPosition)
                currBlock, currPosition = [], []
            else:
                currBlock.append((i[0], i[1]))
                currPosition.append(tokenPositions[idx])
        if currBlock:
            blocks.append(currBlock)
            positions.append(currPosition)
            currBlock, currPosition = [], []
        else:
            currBlock.append((i[0], i[1]))
            currPosition.append(tokenPositions[idx])
        tokenPositions = positions
        tokenPositionsForInterpreter = positionsForInterpreter
        
        return blocks

    def finishLineIfError():                                           # must copy entire line, even if error is found, for error msg
        nonlocal row, col, idx
        while len(text) > idx and text[idx] != "\n":
            advance()
    
    def findTokenEnd(type):                                            # must specify which token is erroneous for error msg
        nonlocal idx, row, col
        if type == ("NUM"):
            while len(text) > idx and (text[idx].isdigit() or text[idx] == ".") and text[idx] != " ":
                advance()
        return idx


    def advance():
        global endifsEncountered, emptyLinesEncountered
        nonlocal idx, row, col

        if idx < len(text):
            if text[idx] != "\n":
                lineCopies[row] += text[idx]                                    # perserving each line for errors outside of lexer
            else:
                strippedLine = lineCopies[-1].strip()
                if strippedLine not in ["endif", "", "endw", "endf"]:
                    lineCopiesForInterpreter[len(lineCopiesForInterpreter)] = (lineCopies[-1], emptyLinesEncountered + endifsEncountered)
                elif strippedLine in ["endif", "endw", "endf"]:
                    endifsEncountered += 1
                elif strippedLine == "":
                    emptyLinesEncountered += 1
            idx += 1; col += 1                                                  

    
    def tokenizer():
        nonlocal idx, row, col
        tokens = []
        

        def record(type, value, posStart, posEnd):
            
            tokens.append((type, value))                                 # must preserve token position information
            tokenPositions.append((posStart, posEnd, row))               # for errors outside of lexer
            
            
        while len(text) > idx:
            
            i = text[idx]
            if i == " ":
                advance()                                                # skip spaces
                continue
            
            elif i == "\n":
                record(symbToTkn[i], i, col, col)
                advance()
                if not lineCopies[-1].strip():
                    row -= 1
                    lineCopies.pop()
                else:
                    correspondingEmptyLines.append(emptyLinesEncountered)
                lineCopies.append("")
                row += 1
                col = 0
            
            elif i.isdigit() or i == ".":                               # for all numbers, convert to tokens here
                num, decimals = "", 0
                start = col
                while len(text) > idx and (i.isdigit() or i == "."):
                    if i == ".":
                        decimals += 1
                        if decimals > 1:
                            record(0, 0, start, findTokenEnd("NUM") - 1)
                            finishLineIfError()
                            return [], error(f"Syntax Error: too many decimals in number", len(tokenPositions) - 1, -1)          # two decimals not allowed for numbers                    
                    num += i; advance()
                    if len(text) > idx:
                        i = text[idx]

                if not decimals:
                    record(TINT, int(num), start, col - 1)              # only floats and integers can exist (all functions will be converted to such if used in mathematical expression)
                else:
                    record(TFLOAT, float(num), start, col - 1)
            
            elif i.isalpha():
                start = col
                word = ""
                while len(text) > idx and (i.isalpha() or i.isdigit()):
                    word += i; advance()
                    if len(text) > idx:
                        i = text[idx]
                if word in keywords:
                    record(TKEYWORD, word, start, col - 1)
                else:
                    record(TIDENTIFIER, word, start, col - 1) #is being recorded
                

            elif i in symbToTkn or i in "|&":

                if tokens and tokens[-1][0] in (TUNARYMINUS, TUNARYPLUS) and (i in symbToTkn or i in "|&") and i not in "([":
                    record(0, 0, col, col)
                    finishLineIfError()
                    print(tokens)
                    return [], error(f"Parser error: expected value expression following unary operator, not operator", len(tokenPositions) - 1, -1)

                elif i in "+-" and ((not tokens or (tokens[-1][1] in symbToTkn and tokens[-1][0] not in [TRPAREN, TRBRACKET]) or tokens[-1][0] == TKEYWORD)):
                    if i in "+":
                        record(TUNARYPLUS, "p", col, col)
                    else:
                        record(TUNARYMINUS, "m", col, col)
                    advance()

                elif i in "&|><!=":
                    start = col
                    operator = ""
                    while len(text) > idx and i in "&|><!=":
                        
                        operator += i; advance()
                        if len(text) > idx:
                            i = text[idx]
                    if operator in symbToTkn:
                        record(symbToTkn[operator], operator, start, col - 1)
                    else:
                        record(0, 0, start, col - 1)
                        finishLineIfError()
                        return [], error(f"Syntax Error: Invalid symbol", len(tokenPositions) - 1, -1)
                else:
                    record(symbToTkn[i], i, col, col)                   
                    advance()
            else:
                record(0, 0, col, col)
                finishLineIfError()
                return [], error(f"Syntax Error: Invalid symbol", len(tokenPositions) - 1, -1)
                                                        
        return tokens, None
    tokens, potentialError = tokenizer()
    if not potentialError:
        return lexLinesWithPosition(tokens), ""
    else:
        return [], potentialError                                     

######################################################################################################################################
# Parser                                                                    # MAKE IT SO EACH ELIF/IF/ELSE REQUIRES AN ENDIF
######################################################################################################################################

##################### VALIDATELHS START
def validateLHS(lhs):
    if lhs[0][0] != TIDENTIFIER:
        return 0
    if len(lhs) > 2:
        return 0
    return -1
#################### VALIDATELHS END

##################### PARSER START #PROB NEED TO GLOBALIZE ROW IDX AND COL

def stateMachine(parsedBlocks): 
    from collections import deque

    prevScope = ""

    ifsIDX, ifs = deque(), deque()

    endState = deque()

    for idx, currBlock in enumerate(parsedBlocks):
        currLHS, currRHS, currOriginalTokenPositions = currBlock
        
        if not currLHS or currLHS[-1][0] == TASSIGN:
            if ifs:
                ifs[-1][-1].append(currBlock)
            else:
                endState.append(currBlock)

        elif currLHS[-1][1] in ["if", "elif", "else", "while", "for"]:
            ifsIDX.append(idx)
            ifs.append((currBlock, deque()))

        elif currLHS[-1][1] in ["endif", "endw", "endf"]:

            if not ifs:
                if currLHS[-1][1] == "endif":
                    return [], error("Interpreter error: 'endif' keyword missing corresponding if keyword", 0, idx)
                elif currLHS[-1][1] == "endw":
                     return [], error("Interpreter error: 'endw' keyword missing corresponding while keyword", 0, idx)
                elif currLHS[-1][-1] == "endf":
                    return [], error("Interpreter error: 'endf' keyword missing corresponding for keyword", 0, idx)
            
            if currLHS[-1][1] == "endw" and ifs[-1][0][0][-1][-1] != "while":
                return [], error(f"Interpreter error: can't close an {ifs[-1][0][0][-1][-1]} keyword with a endw keyword", 0, ifsIDX[-1])
            
            if currLHS[-1][1] == "endif" and ifs[-1][0][0][-1][-1] not in ["if", "elif", "else"]:
                return [], error(f"Interpreter error: can't close an {ifs[-1][0][0][-1][-1]} keyword with a endif keyword", 0, ifsIDX[-1])
            
            if currLHS[-1][1] == "endf" and ifs[-1][0][0][-1][-1] not in ["for"]:
                return [], error(f"Interpreter error: can't close an {ifs[-1][0][0][-1][-1]} keyword with a endf keyword", 0, ifsIDX[-1])

            if len(ifs) >= 2:
                if ifs[-1][0][0][-1][-1] in ["elif", "else"] and ifs[-2][0][0][-1][-1] in ["elif", "else"]:
                    return [], error(f"Interpreter error: can't start an {ifs[-1][0][0][-1][-1]} statement without closing the previous {ifs[-2][0][0][-1][-1]} statement", 0, ifsIDX[-1])
                #if ifs[-1][0][0][-1][-1] == ["elif"] and ifs[-1][-1][0][-1][-1] == "else":
                    #return [], error(f"Interpreter error: an 'elif' statement can't follow an 'else' statement in the same scope", 0, ifsIDX[-1])
                elif ifs[-1][0][0][-1][-1] in ["elif", "else"] and ifs[-2][0][0][-1][-1] in ["while"]:
                    return [], error(f"Interpreter error: {ifs[-1][0][0][-1][-1]} keyword must have a corresponding 'if' keyword", 0, ifsIDX[-1])
                
            if len(ifs) == 1:
                if ifs[-1][0][0][-1][-1] in ["elif", "else"]:
                    return [], error(f"Interpreter error: {ifs[-1][0][0][-1][-1]} keyword must have a corresponding 'if' keyword", 0, ifsIDX[-1])
                
            ifStatementBlock = ifs.pop(); ifStatementBlockIDX = ifsIDX.pop()
            currScope = ifStatementBlock[0][0][-1][-1]

            if ifStatementBlock[0][0][-1][-1] in ["elif", "else"] and prevScope == "else":
                return [], error(f"Interpreter error: an '{ifStatementBlock[0][0][-1][-1]}' statement can't follow an else statement in the same scope", 0, ifStatementBlockIDX)

            prevScope = ifStatementBlock[0][0][-1][-1]

            if ifs:
                ifs[-1][-1].append(ifStatementBlock)
            else:
                endState.append(ifStatementBlock)
    if ifs:
        if ifs[-1][0][0][-1][-1] in ["if", "elif", "else"]:
            return [], error(f"Interpreter error: '{ifs[-1][0][0][-1][-1]}' keyword missing corresponding 'endif' keyword", 0, ifsIDX[-1])
        elif ifs[-1][0][0][-1][-1] in ["while"]:
            return [], error(f"Interpreter error: '{ifs[-1][0][0][-1][-1]}' keyword missing corresponding 'endw' keyword", 0, ifsIDX[-1])
        elif ifs[-1][0][0][-1][-1] in ["for"]:
            return [], error(f"Interpreter error: '{ifs[-1][0][0][-1][-1]}' keyword missing corresponding 'endf' keyword", 0, ifsIDX[-1])
    return endState, ""

                    
        

def passBlocksToParser(blocks):
    import pprint
    
    parsedBlocks = []
    tokenPositionsForInterpreterIDX = 0
    for idx, i in enumerate(blocks):
        LHS, output, originalTokenPositions, potentialError = parser(i, idx)
        if potentialError:
            return [], potentialError
        errorIdxMapInterpreter.append(originalTokenPositions)
        if potentialError:
            return [], potentialError
        if not LHS or (LHS and LHS[-1][-1] not in ["endif", "endw", "endf"]):
            parsedBlocks.append((LHS, output, tokenPositionsForInterpreter[tokenPositionsForInterpreterIDX])) # was parsedBlocks.append((LHS, output, tokenPositionsForInterpreter[tpidx]))
            tokenPositionsForInterpreterIDX += 1
        else:
            parsedBlocks.append((LHS, output, originalTokenPositions))
    return parsedBlocks, ""


def parser(tokens, row ):     #isinstance(tokens[-1][-1], str) and
    import pprint


    

    import pprint                                   
    if isinstance(tokens[-1][-1], str) and tokens[0][0] != TARRAY and tokens[-1][1] in symbToTkn and tokens[-1][0] not in [TRPAREN, TRBRACKET]:
        
        return [], [], [], error("Parser error: expression not allowed to end with operator", len(tokenPositions[row]) - 1, row) # lines can't start with any symbol other than a left paren bracket / 1
    elif isinstance(tokens[-1][-1], str) and tokens[0][0] != TARRAY and tokens[0][1] in symbToTkn and tokens[0][0] not in (TLBRACKET, TLPAREN, TUNARYMINUS, TUNARYPLUS, TNOT):           # and unary operators; lines can't end with any symbol other than a / 2
        return [], [], [], error("Parser error: expression not allowed to start with non unary operator", 0, row)   # right paren bracket

    operator, output, LHS = [], [], [] # LHS holds the assignment entity (left hand side)  / 1
                                       # of any assignment expression to account for SYA's / 2
                                       # inability to diffrentiate LHS and RHS of assignment expressions
                                       

    originalTokenPositions = [] # tracks the idx of each token in source code for error msgs / 1
                                # because SYA is an unstable parsing algo;

    operatorTokenPositions = [] 

    LParenIdx = []       
    
    prev = ("", "") 

    total = []
    arrayState = []
    after = []
    subexpression = []
    

    for idx, i in enumerate(tokens):
        
        #################################################### HANDLE KEYWORDS
        if i[0] == TKEYWORD:

            if i[1] in keywords:
                if idx != 0:
                    return [], [], [], error(f"Parser error: the {i[1]} keyword can only be used at the beggining of a statement", idx, row)
            
            if i[1] in (TELSE, TENDIF, TENDW, TENDF):
                if idx != len(tokens) - 1:
                    return [], [], [], error(f"Parser error: no other tokens can be present in the same line as an {i[1]} keyword", idx + 1, row)      
            LHS.append(i)

        #################################################### HANDLE KEYWORDS

        #################################################### HANDLE VALUES
        if i[0] in (TINT, TFLOAT, TIDENTIFIER, TBOOL, TARRAY):
            if prev[0] in (TINT, TFLOAT, TIDENTIFIER, TRPAREN, TBOOL, TARRAY):
                return [], [], [], error("Parser Error: expected operator, not value", idx, row)
            if prev[1] in [TFOR]:
                if i[0] not in TIDENTIFIER:
                    return [], [], [], error("Parser Error: for loop must be conducted on identifier only", idx, row)
                else:
                    LHS = [i, LHS[-1]]; prev = ("", ""); continue
            output.append(i); originalTokenPositions.append(idx)
           
        #################################################### HANDLE VALUES


        #################################################### HANDLE OPERATORS
        elif i[1] in symbToTkn:

            if i[1] in ["+", "-", "/", "*", "^", "=", ">", ">=", "<", "<=", "==", "!=", "&&", "||", ")"] and prev[1] in ["+", "-", "/", "*", "^", "=", ">", ">=", "<", "<=", "==", "(", "!=", "&&", "||"]:
                return [], [], [], error("Parser Error: repeating operators not allowed", idx, row)
            
            elif i[1] in ",":
                if prev[0] not in [TINT, TFLOAT, TIDENTIFIER, TBOOL, TARRAY]:
                    return [], [], [], error(f"Parser Error: expected value following {i[1]}, not {prev[1]}", idx, row)
                while operator:
                    output.append(operator.pop()); originalTokenPositions.append(operatorTokenPositions.pop())
                if arrayState:
                    arrayState[-1][-1].append(output)
                else:
                    total.extend(output)
                output = []
            
            elif i[0] == TLBRACKET:
                after.append(operator)
                operator = []
                if output:
                    if arrayState:
                        arrayState[-1][-1].append(output)
                    else:
                        total.extend(output)
                    output = []
                arrayState.append([TARRAY, []])
            
            elif i[0] == TRBRACKET: 
                if prev[0] not in [TINT, TFLOAT, TIDENTIFIER, TBOOL, TARRAY, TRBRACKET, TLBRACKET]:
                    return [], [], [], error(f"Parser Error: expected value following {i[1]}, not {prev[1]}", idx, row)
                while operator:
                    output.append(operator.pop()); originalTokenPositions.append(operatorTokenPositions.pop())
                if output:
                    arrayState[-1][-1].append(output)
                output = []
                nest = tuple(arrayState.pop())
                p = after.pop()
                if arrayState:
                    arrayState[-1][-1].append(nest)
                    if p:
                        arrayState[-1][-1].extend(after)
                else:
                    total.append(nest)
                    if p:
                        total.extend(p)
                
                
            elif i[1] in "(":
                if prev[0] in (TINT, TFLOAT, TIDENTIFIER):
                    return [], [], [], error("Parser Error: expected operator, not value expression", idx, row)
                else:
                    LParenIdx.append(idx)
            
            elif i[1] == ")":
                while operator and operator[-1][1] != "(":  
                    output.append(operator.pop()); originalTokenPositions.append(operatorTokenPositions.pop())
                if not operator:
                    return [], [], [], error("Parser Error: unbalanced parenthesis; missing matching left bracket", idx, row)
                operator.pop()
                LParenIdx.pop()
            
            elif i[1] in "=":
                if LHS and LHS[-1][1] in (TIF, TELIF, TWHILE):
                    return [], [], [], error(f"Parser error: '{LHS[-1][1]}' statement must be a truth expression, not an assignment operation", idx, row)
                elif LHS and LHS[-1][1] in (TFOR):
                    return [], [], [], error(f"Parser error: '{LHS[-1][1]}' statement can't be an assignment operation", idx, row)
                if LHS and i[1] in "=":
                    if arrayState:
                        return [], [], [], error(f"Parser error: only value expressions can exist within a list", idx, row)
                    return [], [], [], error(f"Parser error: only one assignment allowed per line; statement can't be an assignment operation", idx, row)
                while operator and operator[-1][1] in ["||", "&&", "==", "!=", "<", ">", ">=", "<=", "+", "-", "*", "/", "^", "p", "m", "!"]:       
                    output.append(operator.pop()); originalTokenPositions.append(operatorTokenPositions.pop())
                LHS = output
                LHS.append(i)
                output = []
                checkLHS = validateLHS(LHS)
                if checkLHS != -1:
                    return [], [], [], error("Parser error: attempted assignment to a non-assignable entity", checkLHS, row)
            
            elif i[1] == "||":
                while operator and operator[-1][1] in ["||","&&", "==", "!=", "<", ">", ">=", "<=", "+", "-", "*", "/", "^", "p", "m", "!"]:         
                    output.append(operator.pop()); originalTokenPositions.append(operatorTokenPositions.pop())

            elif i[1] == "&&":
                while operator and operator[-1][1] in ["&&", "==", "!=", "<", ">", ">=", "<=", "+", "-", "*", "/", "^", "p", "m", "!"]:         
                    output.append(operator.pop()); originalTokenPositions.append(operatorTokenPositions.pop())

            elif i[1] in ["==", "!="]:
                while operator and operator[-1][1] in ["==", "!=", "<", ">", ">=", "<=", "+", "-", "*", "/", "^", "p", "m", "!"]:         
                    output.append(operator.pop()); originalTokenPositions.append(operatorTokenPositions.pop())
            
            elif i[1] in ["<", ">", ">=", "<="]:
                while operator and operator[-1][1] in ["<", ">", ">=", "<=", "+", "-", "*", "/", "^", "p", "m", "!"]:         
                    output.append(operator.pop()); originalTokenPositions.append(operatorTokenPositions.pop()) 


            elif i[1] in "+-":
                while operator and operator[-1][1] in "+-*/^pm!":         
                    output.append(operator.pop()); originalTokenPositions.append(operatorTokenPositions.pop())                
                
            elif i[1] in "*/":
                while operator and operator[-1][1] in "*/^pm!":          
                    output.append(operator.pop()); originalTokenPositions.append(operatorTokenPositions.pop())
                                                                                                                
            elif i[1] in "^":
                while operator and operator[-1][1] in "pm!":          
                    output.append(operator.pop()); originalTokenPositions.append(operatorTokenPositions.pop())

                                                                                                                
            if i[1] not in "[])=,":
                operator.append(i)
                if i[1] != "(":
                    operatorTokenPositions.append(idx)
                                      
        prev = i                                                   

    if LParenIdx:
        return [], [], [], error("Parser Error: unbalanced parenthesis; missing matching right bracket", LParenIdx[0], row)

    while operator:
        output.append(operator.pop()); originalTokenPositions.append(operatorTokenPositions.pop())

    if LHS and LHS[-1][1] in [TIF, TELIF, TWHILE] and not output:
        return [], [], [], error(f"Parser error: the {LHS[-1][1]} keyword can only exist paired with a truth expression", 0, row)
    elif LHS and LHS[-1][1] in [TFOR]:
         if not output:
            return [], [], [], error(f"Parser error: the {LHS[-1][1]} keyword can only exist paired with a loop expression", 0, row)
    #################################################### HANDLE OPERATORS
    hold = []
    if output and total:
        hold = output
    if total:
        output = total
    output.extend(hold)
        
    return LHS, output, originalTokenPositions, ""
##################### PARSER END

######################################################################
# interpreter                                                           #ERROR WITH LINE: a = -cool * 9 -(cool*3+7 - 9/4) ^ 2 - -(cool+6)
######################################################################

global termNumber
def interpretScope(blocksWithScope, lastIf, first): ####need to find a way to return error msgs
    global termNumber
    from collections import deque
    termNumber = 0
    if first:
        output = []
        for i in blocksWithScope:
            res, potentialError = interpretScope(i, True, False)
            if potentialError:
                return [], potentialError
            output.append(res)
        return output, ""
            
    if len(blocksWithScope) == 3 and lastIf:
        res, potentialError = interpreter(blocksWithScope)
        if potentialError:
            return [], potentialError
        return res, ""

    elif len(blocksWithScope) == 2:
        
        if (blocksWithScope[0][0][-1][1] == "if" and lastIf) or (blocksWithScope[0][0][-1][1] in ["else", "elif"] and not lastIf): # if blocksWithScope[0][0][-1][1] in "if" or (blocksWithScope[0][0][-1][1] in ["else", "elif"] and not lastIf)
            res, potentialError = interpreter(blocksWithScope[0])
            if potentialError:
                return [], potentialError
            lastIf = True if res[-1][-1] not in ["false", 0] else False
            elifIsTrue = False 
            collectedRes=[]
            for i in blocksWithScope[1]:
                res, potentialError = interpretScope(i, lastIf, first) #SOMETHING CAN BE DONE HERE maybe break out of loop
                if potentialError:
                    return [], potentialError
                if res:
                    collectedRes.append(res)
                if len(i) == 2 and i[0][0][-1][1] == "elif":
                    if res:
                        break
            return collectedRes, ""
        
        elif blocksWithScope[0][0][-1][1] == "while" and lastIf:
            whileRes = []
            while True:
                res, potentialError = interpreter(blocksWithScope[0])
                if potentialError:
                    return [], potentialError
                elif res[-1][-1] not in ["false", 0]:
                    collectedRes = []
                    for i in blocksWithScope[1]:
                        res, potentialError = interpretScope(i, lastIf, first)
                        if potentialError:
                            return [], potentialError
                        collectedRes.append(res)
                    whileRes.append(collectedRes)
                else:
                    return whileRes, potentialError
                
        elif blocksWithScope[0][0][-1][1] == "for" and lastIf:  

            start, end, jmp = 0, 0, 1
            iteratorVar = blocksWithScope[0][0][0][-1]
            staticIteratorIdentifier = iteratorVar
                       
            end, potentialError = interpreter(blocksWithScope[0])
            if potentialError:
                return [], potentialError
            end = end[-1][-1]
            if end in ["true", "false"]:
                end = 1 if end == "true" else 0
               
            if start == end:
                return [], ""
            
            forRes = []
            change = 0
            while True:
                iteratorVar, impossibleError = interpreter([[(TIDENTIFIER, staticIteratorIdentifier), (TASSIGN, '=')], [(TINT, start + change)], []])
                
                iteratorVar = iteratorVar[-1][-1]
                
                if (end >= start and end > iteratorVar) or (start >= end and iteratorVar > end):
                    collectedRes = []
                    for i in blocksWithScope[1]:
                        res, potentialError = interpretScope(i, lastIf, first)
                        if potentialError:
                            return [], potentialError
                        collectedRes.append(res)
                    forRes.append(collectedRes)
                    change += jmp
                else:
                    return forRes, ""
        return [], ""
    else:
        return [], ""

def interpreter(block):
    global termNumber
    import pprint
    LHS, parsedInput, parsedTokenPositionsInSource = block
    row = parsedTokenPositionsInSource[0][2] if parsedTokenPositionsInSource else None
    
    intermediate = []
    errorIncrement = 1 if LHS and LHS[-1][0] == TASSIGN else 0
    for idx, i in enumerate(parsedInput):
        if i[0] in [TARRAY]:
            for j, n in enumerate(i[1]):
                n = [n] if n[0] == TARRAY else n
                potential, potentialError = interpreter([[], n ,parsedTokenPositionsInSource])
                if potentialError:
                    return [], potentialError
                i[1][j] = potential
                
        
        tokType, value = i[0], i[1]
        if tokType != TARRAY:
            termNumber += 1          
        if tokType in TIDENTIFIER:
            if value in identifiers:
                tokType, value = identifiers[value][0], identifiers[value][1]
            else:
                return [], error("Interpreter error: identifier not defined", parsedTokenPositionsInSource[errorIdxMapInterpreter[row][termNumber]], ("", ""))

        resType, resVal = "", 0

        if tokType in (TINT, TFLOAT, TBOOL, TARRAY):
            intermediate.append((tokType, value))

        elif tokType in (TUNARYMINUS, TUNARYPLUS, TNOT):

            operand = intermediate.pop()
            operandType, operandVal = operand[0], operand[1]
            resType = operandType

            if tokType == TNOT and operandType != TBOOL:
                return [], error("Interpreter error: can't perform logical negation on non-boolean values", parsedTokenPositionsInSource[errorIdxMapInterpreter[row][termNumber]], ("", ""))
            
            elif tokType in [TUNARYMINUS, TUNARYPLUS] and operandType not in [TFLOAT, TINT]:
                return [], error("Interpreter error: can't perform arithmetic negation on non-arithmetic values", parsedTokenPositionsInSource[errorIdxMapInterpreter[row][termNumber]], ("", ""))

            elif tokType == TUNARYMINUS:
                resVal = operandVal * -1
            elif tokType == TUNARYPLUS:
                resVal = operandVal * 1

            elif tokType == TNOT:
                resVal = "false" if operandVal == "true" else "true"
            
            intermediate.append((resType, resVal))

        else:
            if not intermediate:
                break
            right = intermediate.pop()
            left = intermediate.pop()
            
            leftType, leftVal = left[0], left[1]
            rightType, rightVal = right[0], right[1]

            if leftType == TBOOL:
                leftVal = 0 if leftVal == "false" else 1
            if rightType == TBOOL:
                rightVal = 0 if rightVal == "false" else 1

            if tokType in [TGREATERTHAN, TGREATERTHANEQUAL, TLESSTHAN, TLESSTHANEQUAL, TEQUAL, TNOTEQUAL, TAND, TOR]:
                
                if tokType == TGREATERTHAN:
                    resVal = "true" if leftVal > rightVal else "false"
                
                elif tokType == TGREATERTHANEQUAL:
                    resVal = "true" if leftVal >= rightVal else "false"
                
                elif tokType == TLESSTHAN:
                    resVal = "true" if leftVal < rightVal else "false"
                
                elif tokType == TLESSTHANEQUAL:
                    resVal = "true" if leftVal <= rightVal else "false"
                
                elif tokType == TEQUAL:
                    resVal = "true" if leftVal == rightVal else "false"

                elif tokType == TNOTEQUAL:
                    resVal = "true" if leftVal != rightVal else "false"

                elif tokType == TAND:
                    if leftVal != 0 and rightVal != 0:
                        resVal = "true" 
                    else:
                        resVal = "false"

                elif tokType == TOR:
                    if leftVal != 0 or rightVal != 0:
                        resVal = "true"
                    else:
                        resVal = "false"

            elif tokType == TPLUS:
                if leftType == TARRAY:
                    if rightType in [TINT, TFLOAT]:
                        rightVal = [(TINT, 0)] * rightVal
                elif rightType == TARRAY:
                    if leftType in [TINT, TFLOAT]:
                        leftVal = [(TINT, 0)] * leftVal
                resVal = leftVal + rightVal

            elif tokType == TMINUS:
                resVal = leftVal - rightVal

            elif tokType == TDIV:
                if rightVal == 0:
                    return [], error("Interpreter error: attempted division by zero", parsedTokenPositionsInSource[errorIdxMapInterpreter[row][termNumber + 1]], ("", ""))
                else:
                    resVal = leftVal / rightVal

            elif tokType == TMUL:
                resVal = leftVal * rightVal
            
            elif tokType == TEXPO:
                resVal = leftVal ** rightVal
            
            if resVal in ["false", "true"]:
                resType = TBOOL
            elif leftType == TARRAY or rightType == TARRAY:
                resType = TARRAY
            elif resVal % 1 == 0:
                resType, resVal = TINT, int(resVal)
            else:
                resType = TFLOAT
            intermediate.append((resType, resVal))
    if LHS:
        if LHS[-1][0] == TASSIGN:
            identifiers[LHS[0][1]] = intermediate[0]
            return (LHS[0][1], intermediate[0]), ""
        if LHS[-1][1] == "else":
            return [(TBOOL, "true")], ""
    if intermediate:
        return intermediate[0], ""
    else:
        return [], ""
    
############################ ##########################################
# MAIN
######################################################################

def run(sourceCodeFilePath):
    import pprint
    with open(sourceCodeFilePath, 'r') as sourceCode:
        sourceCode = sourceCode.read()

    blocks, potentialError = lexer(sourceCode) 
    if potentialError:                          
        print(potentialError)
        return
    
    
    
    parsedBlocks, potentialError = passBlocksToParser(blocks)
    if potentialError:
        print(potentialError)
        return
    
    blocksWithState, potentialError = stateMachine(parsedBlocks)
    if potentialError:
        print(potentialError)
        return
    
    
    output, potentialError = interpretScope(blocksWithState, False, True)

    if potentialError:
        print(potentialError)
        return
    
    pprint.pprint(output)
    
    return
    
    

run("c:/Users/jeter/Desktop/myLang/source.txt")