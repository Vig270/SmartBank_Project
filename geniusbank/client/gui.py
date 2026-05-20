import tkinter as tk
from tkinter import simpledialog, messagebox
from PIL import Image, ImageTk
import requests
import webbrowser

SERVER_URL = "http://127.0.0.1:5000"

class GeniusBankGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("GeniusBank SaaS Client")
        self.user = None
        self.session = requests.Session()  # <-- persist cookies for login need this for every
        self.login_screen()
        self.root.mainloop()

    # ---------------- LOGIN / REGISTER ----------------
    def login_screen(self):
        for w in self.root.winfo_children(): w.destroy()

        # Load logo
        try:
            image = Image.open("logo.png").resize((300,150))
            self.logo = ImageTk.PhotoImage(image)
            tk.Label(self.root, image=self.logo).pack(pady=10)
        except:
            tk.Label(self.root, text="GeniusBank SaaS", font=("Arial", 18)).pack(pady=10)

        tk.Button(self.root, text="Login", width=20, command=self.login).pack(pady=5)
        tk.Button(self.root, text="Register", width=20, command=self.register).pack(pady=5)

            # ✅ GitHub login button
        tk.Button(self.root, text="Continue with GitHub", width=25, bg="#24292e", fg="white", command=self.login_github).pack(pady=5)

            # Small message
        tk.Label(self.root, text="After GitHub login, view your dashboard in the browser.", fg="gray").pack(pady=5)

    def register(self):
        user_id = simpledialog.askstring("Register", "User ID:")
        name = simpledialog.askstring("Register", "Name:")
        password = simpledialog.askstring("Register", "Password:", show="*")
        if not user_id or not name or not password:
            return

        try:
            res = self.session.post(
                f"{SERVER_URL}/register",
                json={"user_id": user_id, "name": name, "password": password}
            )
        # Try to parse JSON
            try:
                data = res.json()
            except:
                data = {}

        # Check backend's success flag first
            if data.get("success") or res.status_code in (200, 201):
                msg = data.get("message", "User registered successfully!")
                messagebox.showinfo("Success", msg)
            else:
                msg = data.get("message", "Registration failed.")
                messagebox.showerror("Error", msg)

        except Exception as e:
            messagebox.showerror("Error", f"Could not connect to server: {e}")

    def login(self):
        username = simpledialog.askstring("Login", "Username:")
        password = simpledialog.askstring("Login", "Password:", show="*")
        if not username or not password:
            return

        try:
            res = self.session.post(
                f"{SERVER_URL}/login_local",
                json={"username": username, "password": password}
            )
            data = res.json()
            if data.get("status") == "success":
                self.user = data["user"]
                messagebox.showinfo("Success", f"Welcome {self.user['name']}")
                self.dashboard()
            else:
                messagebox.showerror("Error", data.get("message"))
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def login_github(self):
    # Open browser for OAuth
        webbrowser.open("http://127.0.0.1:5000/login/github")
        tk.messagebox.showinfo("Info", "After logging in, enter your GitHub username:")

        gh_username = simpledialog.askstring("GitHub Login", "Enter your GitHub username:")
        if not gh_username: return

        try:
        # Fetch user from server
            res = requests.get(f"{SERVER_URL}/balance", params={"user_id": gh_username})
            data = res.json()
            self.user = {
                "id": gh_username,
                "name": gh_username,
                "balance": data.get("balance", 0),
                "plan": data.get("plan", "FREE")
            }
            messagebox.showinfo("Success", f"Welcome {self.user['name']}")
            self.dashboard()
        except Exception as e:
            messagebox.showerror("Error", f"Could not load GitHub user info: {e}")

    # ---------------- DASHBOARD ----------------
    def dashboard(self):
        for w in self.root.winfo_children(): w.destroy()
        tk.Label(self.root, text=f"Dashboard ({self.user['name']})", font=("Arial",14)).pack(pady=5)

        self.balance_label = tk.Label(self.root, text="")
        self.balance_label.pack(pady=5)

        tk.Button(self.root, text="Deposit", width=20, command=self.deposit).pack(pady=2)
        tk.Button(self.root, text="Withdraw", width=20, command=self.withdraw).pack(pady=2)
        tk.Button(self.root, text="Upgrade PRO", width=20, command=self.upgrade_pro).pack(pady=2)
        tk.Button(self.root, text="Downgrade FREE", width=20, command=self.downgrade_free).pack(pady=2)
        tk.Button(self.root, text="Logout", width=20, command=self.logout).pack(pady=5)

        self.update_balance()

    def update_balance(self):
        try:
            res = requests.get(f"{SERVER_URL}/balance", params={"user_id": self.user["id"]})
            data = res.json()
            self.balance_label.config(text=f"Balance: ${data['balance']:.2f} | Plan: {data['plan']}")
        except:
            self.balance_label.config(text="Balance: Error")

    # ---------------- DEPOSIT / WITHDRAW ----------------
    def deposit(self):
        amount = simpledialog.askfloat("Deposit", "Amount to deposit:")
        if amount is None or amount <= 0: 
            return
        try:
        # <-- use self.session to persist login
            res = self.session.post(f"{SERVER_URL}/deposit", json={"user_id": self.user["id"], "amount": amount})
            data = res.json()
            if res.status_code == 200 and data.get("status") == "success":
                messagebox.showinfo("Success", data["message"])
                self.update_balance()
            else:
                messagebox.showerror("Error", data.get("message"))
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def withdraw(self):
        amount = simpledialog.askfloat("Withdraw", "Amount to withdraw:")
        if amount is None or amount <= 0: 
            return
        try:
            res = self.session.post(f"{SERVER_URL}/withdraw", json={"user_id": self.user["id"], "amount": amount})
            data = res.json()
            if res.status_code == 200 and data.get("status") == "success":
                messagebox.showinfo("Success", data["message"])
                self.update_balance()
            else:
                messagebox.showerror("Error", data.get("message"))
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ---------------- UPGRADE / DOWNGRADE ----------------
    def upgrade_pro(self):
        try:
            res = self.session.post(f"{SERVER_URL}/upgrade_pro", json={"user_id": self.user["id"]})
            data = res.json()
            if data.get("status") == "success":
                self.user["plan"] = "PRO"
                self.update_balance()
            messagebox.showinfo("Info", data.get("message"))
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def downgrade_free(self):
        try:
            res = self.session.post(f"{SERVER_URL}/downgrade_pro", json={"user_id": self.user["id"]})
            data = res.json()
            if data.get("status") == "success":
                self.user["plan"] = "FREE"
                self.update_balance()
            messagebox.showinfo("Info", data.get("message"))
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ---------------- LOGOUT ----------------
    def logout(self):
        self.user = None
        self.login_screen()


if __name__=="__main__":
    GeniusBankGUI()