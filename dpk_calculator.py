import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox
import ctypes
import re
from PIL import Image, ImageTk
# Set DPI awareness for better resolution
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except:
    pass

# Connect to the database
db_path = "db_dkp.db"
connection = sqlite3.connect(db_path)
cursor = connection.cursor()

event_dkp_values = {
    "Archboss": 5,
    "Boonstone Fight": 2,
    "Riftstone Fight": 2,
    "Tax Delivery (Attack)": 2,
    "Tax Delivery (Defense)": 4,
    "Siege": 7,
    "Inter-server Battle": 4
}
# Function to refresh the display window
def refresh_display():
    for row in tree.get_children():
        tree.delete(row)
    cursor.execute("SELECT id, name, dkp_base, dkp_gain, dkp_spent, manual_modifire, note, decay_value FROM dkp_table")
    rows = cursor.fetchall()
    for row in rows:
        tree.insert("", "end", values=row)

# Function to open a window to edit a player's note
def edit_note(event):
    selected_item = tree.selection()
    if not selected_item:
        messagebox.showwarning("Selection Error", "Please select a player to edit the note.")
        return

    player_id, name, dkp_base, dkp_gain, dkp_spent, manual_modifire, note, decay_value = tree.item(selected_item[0])['values']

    # Create a new window for editing the note
    note_window = tk.Toplevel(root)
    note_window.title(f"Edit Note for {name}")
    note_window.geometry("550x550")

    tk.Label(note_window, text=f"Name: {name}").pack(pady=5)
    tk.Label(note_window, text=f"DKP Base: {dkp_base}").pack(pady=5)
    tk.Label(note_window, text=f"DKP Gain: {dkp_gain}").pack(pady=5)
    tk.Label(note_window, text=f"DKP Spent: {dkp_spent}").pack(pady=5)

    tk.Label(note_window, text="Note:").pack(pady=5)
    note_text = tk.Text(note_window, height=10, width=40)
    note_text.insert(tk.END, note if note else "")
    note_text.pack(pady=5)

    def save_note():
        new_note = note_text.get("1.0", tk.END).strip()
        cursor.execute("UPDATE dkp_table SET note = ? WHERE id = ?", (new_note, player_id))
        connection.commit()
        note_window.destroy()
        refresh_display()

    save_button = tk.Button(note_window, text="Save Note", command=save_note)
    save_button.pack(pady=10)

def update_event_dropdown_window():
    global event_dropdown_window
    cursor.execute("SELECT DISTINCT event_name FROM events WHERE event_name != ''")
    events = [row[0] for row in cursor.fetchall()]
    event_dropdown_window["values"] = events

def open_add_players_window():
    add_players_window = tk.Toplevel(root)
    add_players_window.title("Add Players from Text")
    add_players_window.geometry("550x600")

    # Dropdown for selecting event
    tk.Label(add_players_window, text="Select Event:").pack(pady=5)
    global event_dropdown_window
    event_dropdown_window = ttk.Combobox(add_players_window, state="readonly")
    event_dropdown_window.pack(pady=5)

    # Label to display the points of the selected event
    points_label = tk.Label(add_players_window, text="Event Points: N/A")
    points_label.pack(pady=5)

    # Function to update the points label based on the selected event
    def show_event_points(event):
        selected_event = event_dropdown_window.get()
        if selected_event:
            cursor.execute("SELECT event_points FROM events WHERE event_name = ?", (selected_event,))
            result = cursor.fetchone()
            points_label.config(text=f"Event Points: {result[0]}" if result else "Event Points: N/A")

    # Bind the dropdown selection to the points display function
    event_dropdown_window.bind("<<ComboboxSelected>>", show_event_points)

    # Call to populate the dropdown
    update_event_dropdown_window()

    # Button to open Point Manager and update dropdown after closing
    def open_and_refresh_point_manager():
        point_manager_window = open_point_manager()

        # Ensure the window refreshes the dropdown when closed
        if point_manager_window:
            point_manager_window.protocol("WM_DELETE_WINDOW", lambda: (point_manager_window.destroy(), update_event_dropdown_window()))

    tk.Button(add_players_window, text="Manage Events/Points", command=open_and_refresh_point_manager).pack(pady=5)

    # Paste Names from Discord
    tk.Label(add_players_window, text="Paste Names from Discord:").pack(pady=5)
    text_input_window = tk.Text(add_players_window, height=10, width=40)
    text_input_window.pack(pady=5)

    # Add Players from Text
    def add_players_from_text():
        # Get the selected event and points
        selected_event = event_dropdown_window.get()
        if not selected_event:
            messagebox.showwarning("Input Error", "Please select an event.")
            return

        # Retrieve event points from the database
        cursor.execute("SELECT event_points FROM events WHERE event_name = ?", (selected_event,))
        event_points = cursor.fetchone()
        if not event_points:
            messagebox.showwarning("Data Error", "No points found for the selected event.")
            return

        event_points = event_points[0]  # Extract points value

        # Get player names from the text input
        text = text_input_window.get("1.0", tk.END).strip()
        # Updated regex to handle special characters, spaces, and parentheses
        names = set(re.findall(r"@?([\w\-\(\)\s]+)", text))

        if not names:
            messagebox.showwarning("Input Error", "No valid names found.")
            return

        # Process each name and update DKP
        for name in names:
            clean_name = name.strip()  # Remove any extra whitespace

            # Check if the player already exists in the database
            cursor.execute("SELECT id, COALESCE(dkp_base, 0), COALESCE(dkp_gain, 0) FROM dkp_table WHERE name = ?", (clean_name,))
            player_data = cursor.fetchone()

            if player_data:
                # Player exists, increment DKP values
                player_id, current_base, current_gain = player_data
                new_base = current_base + event_points
                new_gain = current_gain + event_points

                cursor.execute(
                    "UPDATE dkp_table SET dkp_base = ?, dkp_gain = ? WHERE id = ?",
                    (new_base, new_gain, player_id)
                )
            else:
                # Player does not exist, insert a new record
                cursor.execute(
                    "INSERT INTO dkp_table (name, dkp_base, dkp_gain) VALUES (?, ?, ?)",
                    (clean_name, event_points, event_points)
                )

        # Commit changes to the database
        connection.commit()
        text_input_window.delete("1.0", tk.END)
        refresh_display()

        # Show a success message
        messagebox.showinfo("Success", f"Added/Updated {len(names)} players with {event_points} DKP Base and Gain each.")


    tk.Button(add_players_window, text="Add Players", command=add_players_from_text).pack(pady=10)


def open_and_refresh_point_manager():
    point_manager_window = open_point_manager()
    if point_manager_window:
        # Update dropdown when the window is closed
        point_manager_window.protocol("WM_DELETE_WINDOW", lambda: (update_event_dropdown_window(), point_manager_window.destroy()))

# Function to open the Point Manager window
def open_point_manager():
    point_manager_window = tk.Toplevel(root)
    point_manager_window.title("Point Manager")
    point_manager_window.geometry("400x400")

    # Event Name Entry
    tk.Label(point_manager_window, text="Event Name:").pack(pady=5)
    event_name_entry = tk.Entry(point_manager_window)
    event_name_entry.pack(pady=5)

    # Event Points Entry
    tk.Label(point_manager_window, text="Event Points:").pack(pady=5)
    event_points_entry = tk.Entry(point_manager_window)
    event_points_entry.pack(pady=5)

    # Function to Add Event
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

        # Check if the event already exists
        cursor.execute("SELECT COUNT(*) FROM events WHERE event_name = ?", (event_name,))
        if cursor.fetchone()[0] > 0:
            messagebox.showwarning("Duplicate Error", "This event already exists in the database.")
            return

        # Insert the event into the events table
        cursor.execute("INSERT INTO events (event_name, event_points) VALUES (?, ?)", (event_name, event_points))
        connection.commit()

        update_delete_event_dropdown()
        update_event_dropdown_window()
        messagebox.showinfo("Success", f"Event '{event_name}' with {event_points} points added.")
        event_name_entry.delete(0, tk.END)
        event_points_entry.delete(0, tk.END)

    # Add Event Button
    add_event_button = tk.Button(point_manager_window, text="Add Event", command=add_event)
    add_event_button.pack(pady=10)

    # Dropdown to Select Event for Deletion
    tk.Label(point_manager_window, text="Select Event to Delete:").pack(pady=5)
    delete_event_dropdown = ttk.Combobox(point_manager_window, state="readonly")
    delete_event_dropdown.pack(pady=5)

    # Function to Populate the Dropdown
    def update_delete_event_dropdown():
        cursor.execute("SELECT DISTINCT event_name FROM events WHERE event_name != ''")
        events = [row[0] for row in cursor.fetchall()]
        delete_event_dropdown["values"] = events

    # Call the Dropdown Update Function
    update_delete_event_dropdown()

    # Function to Delete Selected Event
    def delete_event():
        selected_event = delete_event_dropdown.get()
        if not selected_event:
            messagebox.showwarning("Selection Error", "Please select an event to delete.")
            return

        # Delete the selected event from the `events` table
        cursor.execute("DELETE FROM events WHERE event_name = ?", (selected_event,))
        connection.commit()

        # Update both dropdown menus
        update_delete_event_dropdown()
        update_event_dropdown_window()

        messagebox.showinfo("Success", f"Event '{selected_event}' has been deleted.")

    # Delete Event Button
    delete_event_button = tk.Button(point_manager_window, text="Delete Event", command=delete_event)
    delete_event_button.pack(pady=10)

    return point_manager_window


# Function to delete selected player
def delete_player():
    selected_item = tree.selection()
    if not selected_item:
        messagebox.showwarning("Selection Error", "Please select a player to delete.")
        return

    player_id = tree.item(selected_item[0])['values'][0]
    cursor.execute("DELETE FROM dkp_table WHERE id = ?", (player_id,))
    connection.commit()
    refresh_display()

# Function to modify selected player's DKP
def modify_player():
    selected_item = tree.selection()
    if not selected_item:
        messagebox.showwarning("Selection Error", "Please select a player to modify.")
        return

    player_id = tree.item(selected_item[0])['values'][0]
    dkp_base = dkp_base_entry.get()
    dkp_gain = dkp_gain_entry.get()
    dkp_spent = dkp_spent_entry.get()

    try:
        dkp_base = int(dkp_base) if dkp_base else 0
        dkp_gain = int(dkp_gain) if dkp_gain else 0
        dkp_spent = int(dkp_spent) if dkp_spent else 0
    except ValueError:
        messagebox.showwarning("Input Error", "Please enter valid numbers for DKP values.")
        return

    cursor.execute("""
        UPDATE dkp_table
        SET dkp_base = ?, dkp_gain = ?, dkp_spent = ?
        WHERE id = ?
    """, (dkp_base, dkp_gain, dkp_spent, player_id))
    connection.commit()
    refresh_display()

# GUI setup
root = tk.Tk()
root.title("DKP Calculator")
root.geometry("1800x1000")

# Left-side buttons
frame_left = tk.Frame(root)
frame_left.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)

modify_button = tk.Button(frame_left, text="Modify Player", command=modify_player)
modify_button.pack(pady=5)

delete_button = tk.Button(frame_left, text="Delete Player", command=delete_player)
delete_button.pack(pady=5)

dkp_base_label = tk.Label(frame_left, text="DKP Base:")
dkp_base_label.pack()
dkp_base_entry = tk.Entry(frame_left)
dkp_base_entry.pack()

dkp_gain_label = tk.Label(frame_left, text="DKP Gain:")
dkp_gain_label.pack()
dkp_gain_entry = tk.Entry(frame_left)
dkp_gain_entry.pack()

dkp_spent_label = tk.Label(frame_left, text="DKP Spent:")
dkp_spent_label.pack()
dkp_spent_entry = tk.Entry(frame_left)
dkp_spent_entry.pack()

add_players_window_button = tk.Button(frame_left, text="Add Players from Text", command=open_add_players_window)
add_players_window_button.pack(pady=5)


# Right-side display window
frame_right = tk.Frame(root)
frame_right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)

columns = ("ID", "Name", "DKP Base", "DKP Gain", "DKP Spent", "Manual Modifier", "Note", "Decay Value")
tree = ttk.Treeview(frame_right, columns=columns, show="headings")
for col in columns:
    tree.heading(col, text=col)
    tree.column(col, minwidth=0, width=100, anchor="center")

# Apply style to Treeview with padding for margins inside rows
style = ttk.Style()
style.configure("Treeview", rowheight=30, padding=(5, 5))  # Adjust row height and padding
style.configure("Treeview.Heading", font=("Helvetica", 12, "bold"))

# Bind event to edit note on double-click
tree.bind("<Double-1>", edit_note)

tree.pack(fill=tk.BOTH, expand=True)

logo_image = Image.open("logo_grip.png")
logo_image = logo_image.resize((100, 100))  # Resize the image
logo_photo = ImageTk.PhotoImage(logo_image)
logo_label = tk.Label(root, image=logo_photo)
logo_label.place(relx=0.01, rely=0.85)

# Initial display refresh
refresh_display()

# Run the application
root.mainloop()

# Close the database connection when the app is closed
connection.close()
