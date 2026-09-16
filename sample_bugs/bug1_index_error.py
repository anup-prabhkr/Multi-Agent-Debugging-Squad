"""Sample buggy file: IndexError from accessing a list index out of range."""


def get_last_element(items):
    """Return the last element of a list."""
    # Bug: uses len(items) instead of len(items) - 1
    return items[len(items)]


if __name__ == "__main__":
    numbers = [10, 20, 30, 40, 50]
    print(f"Last element: {get_last_element(numbers)}")
