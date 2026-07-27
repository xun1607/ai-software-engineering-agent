def calculate_average(numbers):
    if numbers is None:
        return 0
    total = sum(numbers)
    # Bug: ZeroDivisionError when numbers is an empty list []
    return total / len(numbers)

def format_user_response(user):
    # Bug: KeyError when email is missing from user dictionary
    name = user.get("name", "Unknown")
    email = user["email"]
    return f"User {name} <{email}>"
