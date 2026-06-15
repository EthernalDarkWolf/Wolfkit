from app.gui.login import LoginApp
from app.gui.attendance import AttendanceApp
from app.utils.db import init_db


def main():
    init_db()

    login_window = LoginApp()
    login_window.run()

    if login_window.authenticated_user:
        app = AttendanceApp(username=login_window.authenticated_user, user_role=login_window.authenticated_role)
        app.run()


if __name__ == "__main__":
    main()


