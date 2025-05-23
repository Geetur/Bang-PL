# Bang
Bang is an interpreted, procedural programming language for algorithmic design/prototypes, or small-scale projects. Bang was created with an emphasis on the developer; it is meant for developers to prototype algorithms, functions, programs, etc. rapidly, and then translate into a more robust language.

Bang is still in development and thus the code in the master branch is meant for debugging! As of May 2025, all of the development going towards this PL will be towards refactoring, and making it overall more scalable, modular, and object-oriented; the refactored codebase will replace this one, and the lexer, parser, and intepreter will all be in seperate files. Everything is in one file currently because I made the master-branch cosebase with no goal in mind other than designing the syntax, and making a working lexer, parser, and interpreter for bang; in other words, I just wanted the core functionality.

Features of Bang are:

| **Features**  | **Description**                                                                                       |
|---------------|-------------------------------------------------------------------------------------------------------|
| **Types**     | Bang currently supports boolean, integer, and float data types with strings on the horizon.          |
| **Expressions** | Bang supports robust mathematical and logical expressions, with a full suite of operators including [+, -, *, /, ^, !, &&] etc. (unary negation and positive is supported though [+,-]). |
| **Variables** | Bang supports dynamically typed user variables with the "=" operator. Variables can be used anywhere a constant value is allowed (in conditions, expressions, loops, etc.). |
| **Conditions** | Bang supports conditional expressions with the [if, elif, else, endif] keywords, which can be paired with any type of expression/value via implicit type conversion. |
| **Loops**     | Bang supports loops via the [for, while, endf, endw] keywords. The for loop requires a variable iterator definition and an end-range value (e.g., 10). The while loop requires a condition. |
| **Data Structures**     | Bang supports dynamic lists with right and left, append, pop, and delete, operations that can append, extend, or delete an arbitrary amount of values, and any value, using the "+/-" operators |
| **Upcoming**  | Functions, hashmaps, tuple assignments, and built-in functions. |

# Example Code

# Sum of 1-n
```
n = 15
sumOfNumbers1ToN = 0
for i n
    sumOfNumbers1ToN = sumOfNumbers1ToN + i
endf

```
# Nested if statements
```
a = 0
if a == 0
    a = a + 1
    if a == 1
        a = a + 1
        if a == 2
            a = 100
        endif
    endif
endif
success = a
```
# if-elif-else block

```
temp = 1
i = 0
birthDay = 15
iEqualsBirthday = 0
monthLength = 30

while temp
    if i == birthday
        iEqualsBirthday = 1
    elif birthday > i
        i = i + 1
        endif
    else
        temp = 0
        endif
    endif
```
# array definition and operation (a = [2, 0, [0,13]] at end of program)
```
a = [1 + 0 + 1 + 0]
birthday = 0
if birthday == 0
    a = a + [0 + 0] + [[0 + 0, 5 + 8]]
endif

```

