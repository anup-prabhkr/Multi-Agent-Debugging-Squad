"""Sample buggy file: Infinite loop — while condition never becomes False."""


def countdown(n):
    """Print a countdown from n to 1."""
    # Bug: n is never decremented, so the loop runs forever
    while n > 0:
        print(n)


if __name__ == "__main__":
    countdown(5)
