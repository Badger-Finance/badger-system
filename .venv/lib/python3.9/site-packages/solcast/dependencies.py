#!/usr/bin/python3


def set_dependencies(source_nodes):
    """Sets contract node dependencies.

    Arguments:
        source_nodes: list of SourceUnit objects.

    Returns: SourceUnit objects where all ContractDefinition nodes contain
             'dependencies' and 'libraries' attributes."""
    symbol_map = get_symbol_map(source_nodes)
    contract_list = [x for i in source_nodes for x in i if x.nodeType == "ContractDefinition"]

    # add immediate dependencies
    for contract in contract_list:
        contract.dependencies = set()
        contract.libraries = dict(
            (_get_type_name(i.typeName), i.libraryName.name)
            for i in contract.nodes
            if i.nodeType == "UsingForDirective"
        )

        # listed dependencies
        for key in contract.contractDependencies:
            contract.dependencies.add(symbol_map[key])

        # using .. for libraries
        for node in contract.children(filters={"nodeType": "UsingForDirective"}):
            ref_node = symbol_map[node.libraryName.referencedDeclaration]
            contract.libraries[_get_type_name(node.typeName)] = ref_node
            contract.dependencies.add(ref_node)

        # imported contracts used as types in assignment
        for node in contract.children(filters={"nodeType": "UserDefinedTypeName"}):
            ref_id = node.referencedDeclaration
            if ref_id in symbol_map:
                contract.dependencies.add(symbol_map[ref_id])

        # imported contracts as types, no assignment
        for node in contract.children(
            filters={"nodeType": "FunctionCall", "expression.nodeType": "Identifier"}
        ):
            if node.typeDescriptions["typeString"].startswith("contract "):
                ref_id = node.expression.referencedDeclaration
                if ref_id in symbol_map:
                    contract.dependencies.add(symbol_map[ref_id])

        # unlinked libraries
        for node in contract.children(filters={"nodeType": "Identifier"}):
            ref_node = symbol_map.get(node.referencedDeclaration)
            if ref_node is None:
                continue
            if ref_node.nodeType in ("EnumDefinition", "StructDefinition"):
                contract.dependencies.add(ref_node)
            if ref_node.nodeType == "ContractDefinition" and ref_node.contractKind == "library":
                contract.dependencies.add(ref_node)

        # prevent recursion errors from self-dependency
        contract.dependencies.discard(contract)

    # add dependencies of dependencies
    for contract in contract_list:
        current_deps = contract.dependencies

        while True:
            expanded_deps = set(x for i in current_deps for x in getattr(i, "dependencies", []))
            expanded_deps |= current_deps
            expanded_deps.discard(contract)

            if current_deps == expanded_deps:
                contract.dependencies = current_deps
                break
            current_deps = expanded_deps

    # convert dependency sets to lists
    for contract in contract_list:
        contract.dependencies = sorted(contract.dependencies, key=lambda k: k.name)
    return source_nodes


def get_symbol_map(source_nodes):
    """Generates a dict of {'id': SourceUnit} used for linking nodes.

    Arguments:
        source_nodes: list of SourceUnit objects."""
    symbol_map = {}
    for node in source_nodes:
        for key, value in ((k, x) for k, v in node.exportedSymbols.items() for x in v):
            try:
                symbol_map[value] = node[key]
            except KeyError:
                # solc >=0.7.2 may include exported symbols that reference
                # other contracts, handle this gracefully
                pass

    return symbol_map


def _get_type_name(node):
    if node is None:
        return None
    if hasattr(node, "name"):
        return node.name
    if hasattr(node, "typeDescriptions"):
        return node.typeDescriptions["typeString"]
    return None
