import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox
import ctypes
import re
from PIL import Image, ImageTk
import pandas as pd
from tkinter import filedialog
from datetime import date
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from datetime import datetime


try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except:
    pass

db_path = "db_dkp.db"
connection = sqlite3.connect(db_path)
cursor = connection.cursor()

def export_to_excel():

    cursor.execute("SELECT * FROM dkp_table")
    rows = cursor.fetchall()

    if not rows:
        messagebox.showwarning("Export Error", "No data to export.")
        return

    headers = [desc[0] for desc in cursor.description]

    df = pd.DataFrame(rows, columns=headers)

    file_path = filedialog.asksaveasfilename(
        defaultextension=".xlsx",
        filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")]
    )

    if not file_path:
        return

    df.to_excel(file_path, index=False)

    messagebox.showinfo("Export Success", f"Data successfully saved to {file_path}.")

def refresh_display():
    for row in tree.get_children():
        tree.delete(row)
    cursor.execute("SELECT id, name, dkp_base, dkp_gain, dkp_spent, manual_modifire, note, decay_value FROM dkp_table")
    rows = cursor.fetchall()
    for row in rows:
        tree.insert("", "end", values=row)

note_window = None

def edit_note(event):
    global note_window

    if note_window is not None:
        note_window.destroy()

    selected_item = tree.selection()
    if not selected_item:
        messagebox.showwarning("Selection Error", "Please select a player to edit.")
        return

    player_id, name, dkp_base, dkp_gain, dkp_spent, manual_modifire, note, decay_value = tree.item(selected_item[0])['values']

    note_window = tk.Toplevel(root)
    note_window.title(f"Edit Player Data for {name}")
    note_window.geometry("550x600")

    tk.Label(note_window, text=f"Name: {name}").pack(pady=5)

    tk.Label(note_window, text="DKP Base:").pack(pady=2)
    dkp_base_var = tk.StringVar(value=str(dkp_base))
    dkp_base_entry = tk.Entry(note_window, textvariable=dkp_base_var, state="readonly")
    dkp_base_entry.pack(pady=2)

    tk.Label(note_window, text="DKP Spent (use + or -):").pack(pady=2)
    dkp_spent_entry = tk.Entry(note_window)
    dkp_spent_entry.insert(0, "0")
    dkp_spent_entry.pack(pady=2)

    def update_dkp_spent():
        try:
            if dkp_spent_entry.get().strip() == "0":

                dkp_base_var.set(str(dkp_base))
            else:
                current_base = int(dkp_base)
                dkp_spent_input = dkp_spent_entry.get().strip()

                if dkp_spent_input.startswith("+"):
                    adjustment = int(dkp_spent_input[1:])
                    new_base = current_base + adjustment
                elif dkp_spent_input.startswith("-"):
                    adjustment = int(dkp_spent_input[1:])
                    new_base = current_base - adjustment
                else:
                    adjustment = int(dkp_spent_input)
                    new_base = current_base + adjustment

                dkp_base_var.set(str(new_base))
        except ValueError:
            dkp_base_var.set("Error")

    dkp_spent_entry.bind("<KeyRelease>", lambda event: update_dkp_spent())

    tk.Label(note_window, text="Note:").pack(pady=5)
    note_text = tk.Text(note_window, height=10, width=40)
    note_text.insert(tk.END, note if note else "")
    note_text.pack(pady=5)

    def save_note():
        try:
            new_dkp_base = int(dkp_base_var.get())
            dkp_spent_input = dkp_spent_entry.get().strip()

            current_spent = int(dkp_spent) if dkp_spent not in (None, 'None') else 0

            if dkp_spent_input.startswith(("+", "-")) and dkp_spent_input[1:].isdigit():
                adjustment = int(dkp_spent_input)
                new_spent = current_spent + adjustment
            elif dkp_spent_input.isdigit():
                new_spent = current_spent + int(dkp_spent_input)
            elif not dkp_spent_input:
                new_spent = current_spent
            else:
                raise ValueError("Invalid input")

            new_note = note_text.get("1.0", tk.END).strip()

            cursor.execute("""
                UPDATE dkp_table
                SET dkp_base = ?, dkp_spent = ?, note = ?
                WHERE id = ?
            """, (new_dkp_base, new_spent, new_note, player_id))

            connection.commit()
            messagebox.showinfo("Success", f"Updated {name}'s DKP Base to {new_dkp_base}.")
            note_window.destroy()
            refresh_display()
        except ValueError:
            messagebox.showwarning("Input Error", "Please enter valid numbers.")

    save_button = tk.Button(note_window, text="Save Changes", command=save_note)
    save_button.pack(pady=10)



def update_event_dropdown_window():
    global event_dropdown_window
    cursor.execute("SELECT DISTINCT event_name FROM events WHERE event_name != ''")
    events = [row[0] for row in cursor.fetchall()]
    event_dropdown_window["values"] = events

add_players_window = None
point_manager_window = None
def open_add_players_window():
    global add_players_window, point_manager_window

    if add_players_window and add_players_window.winfo_exists():
        add_players_window.lift()
        return

    add_players_window = tk.Toplevel(root)
    add_players_window.title("Add Players from Text")
    add_players_window.geometry("550x600")

    def on_close():
        global add_players_window, point_manager_window
        if point_manager_window and point_manager_window.winfo_exists():
            point_manager_window.destroy()
        add_players_window.destroy()
        add_players_window = None

    add_players_window.protocol("WM_DELETE_WINDOW", on_close)

    tk.Label(add_players_window, text="Select Event:").pack(pady=5)
    global event_dropdown_window
    event_dropdown_window = ttk.Combobox(add_players_window, state="readonly")
    event_dropdown_window.pack(pady=5)

    points_label = tk.Label(add_players_window, text="Event Points: N/A")
    points_label.pack(pady=5)

    def show_event_points(event):
        selected_event = event_dropdown_window.get()
        if selected_event:
            cursor.execute("SELECT event_points FROM events WHERE event_name = ?", (selected_event,))
            result = cursor.fetchone()
            points_label.config(text=f"Event Points: {result[0]}" if result else "Event Points: N/A")

    event_dropdown_window.bind("<<ComboboxSelected>>", show_event_points)

    update_event_dropdown_window()

    def open_and_refresh_point_manager():
        point_manager_window = open_point_manager()

        if point_manager_window:
            point_manager_window.protocol("WM_DELETE_WINDOW", lambda: (point_manager_window.destroy(), update_event_dropdown_window()))

    tk.Button(add_players_window, text="Manage Events/Points", command=open_and_refresh_point_manager).pack(pady=5)

    tk.Label(add_players_window, text="Paste Names from Discord:").pack(pady=5)
    text_input_window = tk.Text(add_players_window, height=10, width=40)
    text_input_window.pack(pady=5)


    def add_players_from_text():

        selected_event = event_dropdown_window.get()
        if not selected_event:
            messagebox.showwarning("Input Error", "Please select an event.")
            return

        cursor.execute("SELECT event_points FROM events WHERE event_name = ?", (selected_event,))
        event_points = cursor.fetchone()
        if event_points is None:
            messagebox.showwarning("Data Error", "No points found for the selected event.")
            return

        event_points = event_points[0] 

        text = text_input_window.get("1.0", tk.END).strip()
        names = set(re.findall(r"@?([\w\-\(\)\s]+)", text))

        if not names:
            messagebox.showwarning("Input Error", "No valid names found.")
            return

        for name in names:
            cursor.execute("SELECT id, COALESCE(dkp_base, 0), COALESCE(dkp_gain, 0) FROM dkp_table WHERE name = ?", (name,))
            player_data = cursor.fetchone()

            if player_data:
          
                player_id, current_base, current_gain = player_data
                new_base = current_base + event_points

                cursor.execute(
                    "UPDATE dkp_table SET dkp_base = ?, dkp_gain = dkp_gain + ? WHERE id = ?",
                    (new_base, event_points, player_id)
                )
            else:
          
                cursor.execute(
                    "INSERT INTO dkp_table (name, dkp_base, dkp_gain) VALUES (?, ?, ?)",
                    (name, event_points, event_points)
                )

        connection.commit()
        text_input_window.delete("1.0", tk.END)
        refresh_display()

        messagebox.showinfo("Success", f"Added/Updated {len(names)} players with {event_points} DKP points each.")


    tk.Button(add_players_window, text="Add Players", command=add_players_from_text).pack(pady=10)


def open_and_refresh_point_manager():
    point_manager_window = open_point_manager()
    if point_manager_window:

        point_manager_window.protocol("WM_DELETE_WINDOW", lambda: (update_event_dropdown_window(), point_manager_window.destroy()))


decay_window = None
set_decay_window = None 

def open_decay_window():
    global decay_window

    if decay_window and tk.Toplevel.winfo_exists(decay_window):
        decay_window.lift()
        return

    decay_window = tk.Toplevel(root)
    decay_window.title("Decay Managing")
    decay_window.geometry("500x300")

    cursor.execute("SELECT last_decay_date FROM decay LIMIT 1")
    last_decay_date = cursor.fetchone()[0]

    if last_decay_date:
        from datetime import date, datetime
        print(f"last_decay_date: {last_decay_date}")
        last_date = datetime.strptime(last_decay_date, "%Y-%m-%d").date()
        today_date = date.today()
        days_since_last_decay = (today_date - last_date).days
    else:
        days_since_last_decay = 0


    next_decay_label = tk.Label(decay_window, text=f"Next Decay in: {30 - days_since_last_decay} days")
    next_decay_label.pack(pady=10)


    tk.Label(decay_window, text="Enter Decay Percentage (+/-):").pack(pady=10)
    decay_entry = tk.Entry(decay_window)
    decay_entry.pack(pady=5)

    def apply_decay():
        try:
            decay_input = decay_entry.get().strip()
            if not decay_input:
                messagebox.showwarning("Input Error", "Please enter a valid decay value.")
                return

            if not messagebox.askyesno("Confirm Decay", "Are you sure you want to apply decay for all players?"):
                return

            decay_value = float(decay_input)

            cursor.execute("SELECT id, dkp_base FROM dkp_table")
            players = cursor.fetchall()

            for player_id, dkp_base in players:
                if decay_input.startswith("+"):
                    new_dkp_base = dkp_base + (dkp_base * (decay_value / 100))
                elif decay_input.startswith("-"):
                    new_dkp_base = dkp_base - (dkp_base * (abs(decay_value) / 100))
                else:
                    new_dkp_base = dkp_base - (dkp_base * (decay_value / 100))

                cursor.execute("UPDATE dkp_table SET dkp_base = ? WHERE id = ?", (round(new_dkp_base), player_id))

            today_date = date.today().isoformat()
            cursor.execute("UPDATE decay SET last_decay_date = ? WHERE id = 1", (today_date,))

            connection.commit()
            decay_window.destroy()
            refresh_display()
            messagebox.showinfo("Success", f"Applied a {decay_value}% decay to all players.")
        except ValueError:
            messagebox.showwarning("Input Error", "Please enter a valid number.")

    tk.Button(decay_window, text="Apply Decay", command=apply_decay).pack(pady=10)

    def open_set_decay_window():
        global set_decay_window

        if set_decay_window and tk.Toplevel.winfo_exists(set_decay_window):
            set_decay_window.lift()
            return

        set_decay_window = tk.Toplevel(decay_window)
        set_decay_window.title("Set/Auto Decay")
        set_decay_window.geometry("400x250")

        cursor.execute("SELECT decay_percent_month, last_decay_date FROM decay LIMIT 1")
        decay_data = cursor.fetchone()

        current_decay_rate = decay_data[0] if decay_data else 0
        last_decay_date = decay_data[1] if decay_data else "Not Set"

        tk.Label(set_decay_window, text=f"Last Decay Date: {last_decay_date}").pack(pady=5)

        tk.Label(set_decay_window, text="Set Decay Rate (%) per Month:").pack(pady=10)
        decay_rate_entry = tk.Entry(set_decay_window)
        decay_rate_entry.insert(0, str(current_decay_rate))
        decay_rate_entry.pack(pady=5)

        def save_decay_rate():
            global set_decay_window
            try: 
                decay_rate = float(decay_rate_entry.get().strip())

                cursor.execute("UPDATE decay SET decay_percent_month = ? WHERE id = 1", (decay_rate,))

                connection.commit()
                messagebox.showinfo("Success", f"Decay rate set to {decay_rate}% per month.")
                set_decay_window.destroy()
                set_decay_window = None

                update_decay_days_label()
            except ValueError:
                messagebox.showwarning("Input Error", "Please enter a valid number.")

        tk.Button(set_decay_window, text="Save Decay Rate", command=save_decay_rate).pack(pady=10)

        def on_set_close():
            global set_decay_window
            if set_decay_window:
                set_decay_window.destroy()
                set_decay_window = None

        set_decay_window.protocol("WM_DELETE_WINDOW", on_set_close)

    tk.Button(decay_window, text="Set/Auto Decay", command=open_set_decay_window).pack(pady=10)

    def on_close():
        global decay_window
        if decay_window:
            decay_window.destroy()
            decay_window = None

    decay_window.protocol("WM_DELETE_WINDOW", on_close)
    

def open_point_manager():
    global point_manager_window

    if point_manager_window and point_manager_window.winfo_exists():
        point_manager_window.lift()
        return

    point_manager_window = tk.Toplevel(root)
    point_manager_window.title("Point Manager")
    point_manager_window.geometry("400x400")

    def on_close():
        global point_manager_window
        point_manager_window.destroy()
        point_manager_window = None

    point_manager_window.protocol("WM_DELETE_WINDOW", on_close)

    tk.Label(point_manager_window, text="Event Name:").pack(pady=5)
    event_name_entry = tk.Entry(point_manager_window)
    event_name_entry.pack(pady=5)

    tk.Label(point_manager_window, text="Event Points:").pack(pady=5)
    event_points_entry = tk.Entry(point_manager_window)
    event_points_entry.pack(pady=5)

    def add_event():
        event_name = event_name_entry.get().strip()
        try:
            event_points = int(event_points_entry.get().strip())
        except ValueError:
            messagebox.showwarning("Input Error", "Please enter a valid number for event points.")
            return

        if not event_name:
            messagebox.showwarning("Input Error", "Event name cannot be empty.")
            return

        cursor.execute("SELECT COUNT(*) FROM events WHERE event_name = ?", (event_name,))
        if cursor.fetchone()[0] > 0:
            messagebox.showwarning("Duplicate Error", "This event already exists in the database.")
            return

        cursor.execute("INSERT INTO events (event_name, event_points) VALUES (?, ?)", (event_name, event_points))
        connection.commit()

        update_delete_event_dropdown()
        update_event_dropdown_window()
        messagebox.showinfo("Success", f"Event '{event_name}' with {event_points} points added.")
        event_name_entry.delete(0, tk.END)
        event_points_entry.delete(0, tk.END)
        
    add_event_button = tk.Button(point_manager_window, text="Add Event", command=add_event)
    add_event_button.pack(pady=10)

    tk.Label(point_manager_window, text="Select Event to Delete:").pack(pady=5)
    delete_event_dropdown = ttk.Combobox(point_manager_window, state="readonly")
    delete_event_dropdown.pack(pady=5)

    def update_delete_event_dropdown():
        cursor.execute("SELECT DISTINCT event_name FROM events WHERE event_name != ''")
        events = [row[0] for row in cursor.fetchall()]
        delete_event_dropdown["values"] = events

    update_delete_event_dropdown()

    def delete_event():
        selected_event = delete_event_dropdown.get()
        if not selected_event:
            messagebox.showwarning("Selection Error", "Please select an event to delete.")
            return

        cursor.execute("DELETE FROM events WHERE event_name = ?", (selected_event,))
        connection.commit()

        update_delete_event_dropdown()
        update_event_dropdown_window()

        messagebox.showinfo("Success", f"Event '{selected_event}' has been deleted.")

    delete_event_button = tk.Button(point_manager_window, text="Delete Event", command=delete_event)
    delete_event_button.pack(pady=10)

    return point_manager_window


def delete_player():
    selected_item = tree.selection()
    if not selected_item:
        messagebox.showwarning("Selection Error", "Please select a player to delete.")
        return

    player_id, player_name = tree.item(selected_item[0])['values'][0], tree.item(selected_item[0])['values'][1]

    confirm = messagebox.askyesno("Confirm Deletion", f"Are you sure you want to delete {player_name}?")
    if not confirm:
        return

    cursor.execute("DELETE FROM dkp_table WHERE id = ?", (player_id,))
    connection.commit()
    refresh_display()

    messagebox.showinfo("Success", f"{player_name} has been successfully deleted.")

import matplotlib.pyplot as plt

def show_top_15_dkp_graph():
    # Create a new graph window
    graph_window = tk.Toplevel(root)
    graph_window.title("DKP Base Points Graph")
    graph_window.geometry("900x600")

    # Query the database for players sorted by DKP Base Points
    cursor.execute("SELECT name, dkp_base FROM dkp_table ORDER BY dkp_base DESC")
    players = cursor.fetchall()

    if not players:
        messagebox.showinfo("No Data", "No players found in the database.")
        graph_window.destroy()
        return

    # Prepare data for plotting
    names = [player[0] for player in players]
    dkp_base_values = [player[1] for player in players]

    # Create the figure and axis for the plot
    fig = Figure(figsize=(12, 8))
    ax = fig.add_subplot(111)

    # Plot the horizontal bar chart
    ax.barh(names, dkp_base_values, color='skyblue')
    ax.set_xlabel('DKP Base Points')
    ax.set_title('All Players Sorted by DKP Base Points')

    # Add values to each bar
    for index, value in enumerate(dkp_base_values):
        ax.text(value + 1, index, f'{value}', va='center')

    # Invert y-axis to have the highest points on top
    ax.invert_yaxis()

    # Embed the figure inside the Tkinter window
    canvas = FigureCanvasTkAgg(fig, master=graph_window)
    canvas.draw()
    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

# GUI setup
root = tk.Tk()
root.title("DKP Calculator")
root.geometry("1800x1000")
root.resizable(False, False)

# Left-side buttons
frame_left = tk.Frame(root)
frame_left.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)

add_players_window_button = tk.Button(frame_left, text="Add Players from Text", command=open_add_players_window)
add_players_window_button.pack(pady=5)

decay_button = tk.Button(frame_left, text="Decay Managing", command=open_decay_window)
decay_button.pack(pady=5)

delete_button = tk.Button(frame_left, text="Delete Player", command=delete_player)
delete_button.pack(pady=50)

filter_frame = tk.Frame(root)
filter_frame.pack(fill="x", padx=10, pady=5)

filter_entry = tk.Entry(filter_frame, width=50)
filter_entry.grid(row=0, column=1, sticky="e", padx=5, pady=5)

filter_label = tk.Label(filter_frame, text="Filter by Name:")
filter_label.grid(row=0, column=0, sticky="w", padx=5)

graph_button = tk.Button(frame_left, text="DKP Graph", command=show_top_15_dkp_graph)
graph_button.pack(pady=10)

frame_right = tk.Frame(root)
frame_right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)

scrollbar = tk.Scrollbar(frame_right)
scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

columns = ("ID", "Name", "DKP Base", "DKP Gain", "DKP Spent", "Manual Modifier", "Note", "Decay Value")
tree = ttk.Treeview(frame_right, columns=columns, show="headings")
for col in columns:
    tree.heading(col, text=col)
    tree.column(col, minwidth=0, width=100, anchor="center")

style = ttk.Style()
style.configure("Treeview", rowheight=30, padding=(5, 5))
style.configure("Treeview.Heading", font=("Helvetica", 12, "bold"))

tree.bind("<Double-1>", edit_note)

tree.pack(fill=tk.BOTH, expand=True)
scrollbar.config(command=tree.yview)

def filter_treeview(event):
    search_term = filter_entry.get().strip().lower()
    
    for item in tree.get_children():
        tree.delete(item)
    
    cursor.execute("""
        SELECT id, name, dkp_base, dkp_gain, dkp_spent, manual_modifire, note, decay_value
        FROM dkp_table
        WHERE LOWER(name) LIKE ?
    """, ('%' + search_term + '%',))
    
    rows = cursor.fetchall()
    for row in rows:
        tree.insert('', 'end', values=row)

filter_entry.bind("<KeyRelease>", filter_treeview)

gorilla_image = Image.open("gorilla_wall.webp")
gorilla_image = gorilla_image.resize((200, 200))
gorilla_photo = ImageTk.PhotoImage(gorilla_image)

gorilla_label = tk.Label(root, image=gorilla_photo)
gorilla_label.place(relx=0.005, rely=0.788)

gorilla_label.image = gorilla_photo

def update_decay_days_label():
    cursor.execute("SELECT last_decay_date, decay_percent_month FROM decay LIMIT 1")
    decay_data = cursor.fetchone()

    if decay_data:
        last_decay_date = decay_data[0]
        if last_decay_date:
            from datetime import date, datetime

            last_decay_date = last_decay_date.strip()
            last_date = datetime.strptime(last_decay_date, "%Y-%m-%d").date()
            today_date = date.today()

            days_since_last_decay = (today_date - last_date).days

            days_left = 30 - days_since_last_decay

            if days_left <= 0:
                apply_decay_auto()
                days_left = 30
        else:
            days_left = "Not Set"
    else:
        days_left = "Not Set"

    decay_days_label.config(text=f"Next Decay in: {days_left} days")


def apply_decay_auto():
    cursor.execute("SELECT decay_percent_month FROM decay LIMIT 1")
    decay_rate_data = cursor.fetchone()

    if decay_rate_data:
        decay_rate = decay_rate_data[0]

        cursor.execute("SELECT id, dkp_base FROM dkp_table")
        players = cursor.fetchall()

        for player_id, dkp_base in players:
            new_dkp_base = dkp_base - (dkp_base * (decay_rate / 100))
            cursor.execute("UPDATE dkp_table SET dkp_base = ? WHERE id = ?", (round(new_dkp_base), player_id))

        today_date = date.today().isoformat()
        cursor.execute("UPDATE decay SET last_decay_date = ? WHERE id = 1", (today_date,))

        connection.commit()
        refresh_display()
        print(f"Applied {decay_rate}% decay to all players.")


decay_days_label = tk.Label(frame_left, text="Next Decay in: Not Set")
decay_days_label.pack(pady=10)

update_decay_days_label()


save_to_excel_button = tk.Button(root, text="Save to Excel", command=export_to_excel)
save_to_excel_button.place(relx=0.03, rely=0.70)

refresh_display()

root.mainloop()

connection.close()
