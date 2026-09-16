"""Sample buggy file: TypeError from concatenating str and int."""


def format_greeting(name, age):
    """Return a greeting string with name and age."""
    # Bug: concatenating string with integer without conversion
    greeting = "Hello, " + name + "! You are " + age + " years old."
    return greeting


if __name__ == "__main__":
    print(format_greeting("Alice", 30))
