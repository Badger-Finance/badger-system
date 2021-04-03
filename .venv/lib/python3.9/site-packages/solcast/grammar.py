#!/usr/bin/python3

# This list is incomplete - feel free to add to it and open a pull request
# https://solidity.readthedocs.io/en/latest/miscellaneous.html#language-grammar

BASE_NODE_TYPES = {
    "ContractPart": [
        "EnumDefinition",
        "EventDefinition",
        "FunctionDefinition",
        "ModifierDefinition",
        "StateVariableDeclaration",
        "StructDefinition",
        "UsingForDeclaration",
    ],
    "Expression": [
        "Assignment",
        "BinaryOperation",
        "Conditional",
        "FunctionCall",
        "IndexAccess",
        "MemberAccess",
        "NewExpression",
        "UnaryOperation",
        "VariableDeclaration",
    ],
    "PrimaryExpression": [
        "BooleanLiteral",
        "ElementaryTypeNameExpression",
        "HexLiteral",
        "Identifier",
        "NumberLiteral",
        "StringLiteral",
        "TupleExpression",
    ],
    "Statement": [
        "Break",
        "Continue",
        "DoWhileStatement",
        "EmitStatement",
        "ExpressionStatement",
        "ForStatement",
        "IfStatement",
        "InlineAssemblyStatement",
        "PlaceholderStatement",
        "Return",
        "SimpleStatement",
        "Throw",
        "WhileStatement",
    ],
    "TypeName": [
        "ArrayTypeName",
        "ElementaryTypeName",
        "FunctionTypeName",
        "Mapping",
        "UserDefinedTypeName",
    ],
}
