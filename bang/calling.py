"""Argument binding shared by checking and execution; values are never evaluated here."""


def bind_arguments(parameters, arguments, keyword_names=(), *, variadic_name=None):
    names = [name for name, _has_default in parameters]
    allowed = set(names)
    labels = keyword_names or (None,) * len(arguments)
    bound = {} if variadic_name is None else {variadic_name: []}
    position = 0
    named = False
    for label, value in zip(labels, arguments, strict=True):
        if label is None:
            if named:
                raise ValueError("positional arguments must precede named arguments")
            if variadic_name is not None:
                bound[variadic_name].append(value)
                continue
            if position >= len(names):
                raise ValueError("too many positional arguments")
            label = names[position]
            position += 1
        else:
            named = True
            if label not in allowed:
                raise ValueError(f"unknown argument '{label}'")
        if label in bound:
            raise ValueError(f"multiple values for argument '{label}'")
        bound[label] = value
    for name, has_default in parameters:
        if name not in bound and not has_default:
            raise ValueError(f"missing required argument '{name}'")
    return bound
