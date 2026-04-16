"""
Buggy Python code to generate a real AttributeError stacktrace for testing.
The bug: UserService.current_user is never set (None),
then code tries to access .name on it → AttributeError: 'NoneType' object has no attribute 'name'
"""

class User:
    def __init__(self, name: str, email: str):
        self.name = name
        self.email = email


class UserService:
    def __init__(self):
        self.current_user = None   # BUG: should be initialized from DB or auth context

    def get_username(self) -> str:
        # Line 17 — AttributeError will fire here
        return self.current_user.name

    def get_email(self) -> str:
        return self.current_user.email

    def process_user(self):
        username = self.get_username()
        print(f"Processing request for user: {username}")


class OrderController:
    def __init__(self):
        self.user_service = UserService()

    def handle_order(self, order_id: int):
        print(f"Handling order #{order_id}")
        self.user_service.process_user()


def main():
    controller = OrderController()
    controller.handle_order(order_id=42)


if __name__ == "__main__":
    main()
