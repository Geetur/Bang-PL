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
                count = sum(label is None for label in labels)
                raise ValueError(
                    f"too many positional arguments (expected at most {len(names)}, got {count})"
                )
            label = names[position]
            position += 1
        else:
            named = True
            if label not in allowed:
                expected = ", ".join(names[:12]) or "(none)"
                if len(names) > 12:
                    expected += ", ..."
                raise ValueError(f"unknown argument '{label}'; declared parameters: {expected}")
        if label in bound:
            raise ValueError(f"multiple values for argument '{label}'")
        bound[label] = value
    for name, has_default in parameters:
        if name not in bound and not has_default:
            hint = (
                f"; '{name}' is a named option: use {name}=...; "
                f"positional arguments are collected in '{variadic_name}'"
                if variadic_name is not None else ""
            )
            raise ValueError(f"missing required argument '{name}'" + hint)
    return bound
