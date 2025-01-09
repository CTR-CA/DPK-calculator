import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox
import ctypes
import re
from PIL import Image, ImageTk
import pandas as pd
from tkinter import filedialog

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except:
    pass

# Connect to the database
db_path = "db_dkp.db"
connection = sqlite3.connect(db_path)
cursor = connection.cursor()

#save to excel
def export_to_excel():
    # Get the data from the database
    cursor.execute("SELECT * FROM dkp_table")
    rows = cursor.fetchall()

    if not rows:
        messagebox.showwarning("Export Error", "No data to export.")
        return

    # Define column headers
    headers = [desc[0] for desc in cursor.description]

    # Create a DataFrame
    df = pd.DataFrame(rows, columns=headers)

    # Open a Save As dialog to choose the file location
    file_path = filedialog.asksaveasfilename(
        defaultextension=".xlsx",
        filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")]
    )

    if not file_path:
        return  # User canceled the save dialog

    # Export the DataFrame to Excel
    df.to_excel(file_path, index=False)

    messagebox.showinfo("Export Success", f"Data successfully saved to {file_path}.")

# Function to refresh the display window
def refresh_display():
    for row in tree.get_children():
        tree.delete(row)
    cursor.execute("SELECT id, name, dkp_base, dkp_gain, dkp_spent, manual_modifire, note, decay_value FROM dkp_table")
    rows = cursor.fetchall()
    for row in rows:
        tree.insert("", "end", values=row)

# Function to open a window to edit a player's note
note_window = None

def edit_note(event):
    global note_window

    # If there's an existing note window, close it first
    if note_window is not None:
        note_window.destroy()

    selected_item = tree.selection()
    if not selected_item:
        messagebox.showwarning("Selection Error", "Please select a player to edit.")
        return

    # Unpack the correct number of values
    player_id, name, dkp_base, dkp_gain, dkp_spent, manual_modifire, note, decay_value = tree.item(selected_item[0])['values']

    # Create a new window for editing
    note_window = tk.Toplevel(root)
    note_window.title(f"Edit Player Data for {name}")
    note_window.geometry("550x600")

    # Editable fields for DKP Base and Spent
    tk.Label(note_window, text=f"Name: {name}").pack(pady=5)

    # DKP Base Entry (Read-Only)
    tk.Label(note_window, text="DKP Base:").pack(pady=2)
    dkp_base_var = tk.StringVar(value=str(dkp_base))
    dkp_base_entry = tk.Entry(note_window, textvariable=dkp_base_var, state="readonly")
    dkp_base_entry.pack(pady=2)

    # DKP Spent Entry
    tk.Label(note_window, text="DKP Spent (use + or -):").pack(pady=2)
    dkp_spent_entry = tk.Entry(note_window)
    dkp_spent_entry.insert(0, "0")
    dkp_spent_entry.pack(pady=2)

    # Function to update DKP Spent
    def update_dkp_spent():
        try:
            if dkp_spent_entry.get().strip() == "0":
                # If 0 is entered, keep the existing spent value
                dkp_base_var.set(str(dkp_base))
            else:
                current_base = int(dkp_base)
                dkp_spent_input = dkp_spent_entry.get().strip()

                # Handle + and - inputs
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

    # Bind DKP Spent entry to trigger recalculation
    dkp_spent_entry.bind("<KeyRelease>", lambda event: update_dkp_spent())

    # Note field
    tk.Label(note_window, text="Note:").pack(pady=5)
    note_text = tk.Text(note_window, height=10, width=40)
    note_text.insert(tk.END, note if note else "")
    note_text.pack(pady=5)

    # Save changes to the database
    def save_note():
        try:
            new_dkp_base = int(dkp_base_var.get())
            dkp_spent_input = dkp_spent_entry.get().strip()

            # Ensure dkp_spent is an integer or 0 if None
            current_spent = int(dkp_spent) if dkp_spent not in (None, 'None') else 0

            # Check if dkp_spent_input is a valid number
            if dkp_spent_input.startswith(("+", "-")) and dkp_spent_input[1:].isdigit():
                adjustment = int(dkp_spent_input)
                new_spent = current_spent + adjustment
            elif dkp_spent_input.isdigit():
                new_spent = current_spent + int(dkp_spent_input)
            elif not dkp_spent_input:  # If the input is empty, keep the current spent
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


    # Save button
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

    # If the window already exists, bring it to the front
    if add_players_window and add_players_window.winfo_exists():
        add_players_window.lift()
        return

    # Create a new "Add Players" window
    add_players_window = tk.Toplevel(root)
    add_players_window.title("Add Players from Text")
    add_players_window.geometry("550x600")

    # Function to handle window closing
    def on_close():
        global add_players_window, point_manager_window
        if point_manager_window and point_manager_window.winfo_exists():
            point_manager_window.destroy()  # Close Point Manager if it's open
        add_players_window.destroy()
        add_players_window = None

    # Set the window close protocol
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
        # Ensure an event is selected
        selected_event = event_dropdown_window.get()
        if not selected_event:
            messagebox.showwarning("Input Error", "Please select an event.")
            return

        # Fetch event points from the database
        cursor.execute("SELECT event_points FROM events WHERE event_name = ?", (selected_event,))
        event_points = cursor.fetchone()
        if event_points is None:
            messagebox.showwarning("Data Error", "No points found for the selected event.")
            return

        event_points = event_points[0]  # Unpack the tuple

        # Get player names from the text input
        text = text_input_window.get("1.0", tk.END).strip()
        names = set(re.findall(r"@?([\w\-\(\)\s]+)", text))

        if not names:
            messagebox.showwarning("Input Error", "No valid names found.")
            return

        # Loop through names and update the database
        for name in names:
            cursor.execute("SELECT id, COALESCE(dkp_base, 0), COALESCE(dkp_gain, 0) FROM dkp_table WHERE name = ?", (name,))
            player_data = cursor.fetchone()

            if player_data:
                # Update existing player
                player_id, current_base, current_gain = player_data
                new_base = current_base + event_points

                cursor.execute(
                    "UPDATE dkp_table SET dkp_base = ?, dkp_gain = dkp_gain + ? WHERE id = ?",
                    (new_base, event_points, player_id)
                )
            else:
                # Insert new player
                cursor.execute(
                    "INSERT INTO dkp_table (name, dkp_base, dkp_gain) VALUES (?, ?, ?)",
                    (name, event_points, event_points)
                )

        # Commit changes and clear the text input
        connection.commit()
        text_input_window.delete("1.0", tk.END)
        refresh_display()

        # Display a success message
        messagebox.showinfo("Success", f"Added/Updated {len(names)} players with {event_points} DKP points each.")


    tk.Button(add_players_window, text="Add Players", command=add_players_from_text).pack(pady=10)


def open_and_refresh_point_manager():
    point_manager_window = open_point_manager()
    if point_manager_window:
        # Update dropdown when the window is closed
        point_manager_window.protocol("WM_DELETE_WINDOW", lambda: (update_event_dropdown_window(), point_manager_window.destroy()))


decay_window = None

def open_decay_window():
    global decay_window

    # Check if the window is already open
    if decay_window and tk.Toplevel.winfo_exists(decay_window):
        decay_window.lift()
        return

    decay_window = tk.Toplevel(root)
    decay_window.title("Decay Managing")
    decay_window.geometry("500x250")

    # Label and Entry for Decay
    tk.Label(decay_window, text="Enter Decay Percentage (+/-):").pack(pady=10)
    decay_entry = tk.Entry(decay_window)
    decay_entry.pack(pady=5)

    # Apply Decay Button
    def apply_decay():
        try:
            decay_input = decay_entry.get().strip()
            if not decay_input:
                messagebox.showwarning("Input Error", "Please enter a valid decay value.")
                return

            # Confirmation dialog
            if not messagebox.askyesno("Confirm Decay", "Are you sure you want to apply decay for all players?"):
                return

            # Determine decay value
            decay_value = float(decay_input)

            # Apply decay to all players
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

            connection.commit()
            decay_window.destroy()
            refresh_display()
            messagebox.showinfo("Success", f"Applied a {decay_value}% decay to all players.")
        except ValueError:
            messagebox.showwarning("Input Error", "Please enter a valid number.")

    # Button to apply decay
    tk.Button(decay_window, text="Apply Decay", command=apply_decay).pack(pady=10)

    # Handle window close to clear the variable
    def on_close():
        global decay_window
        if decay_window:
            decay_window.destroy()
            decay_window = None

    decay_window.protocol("WM_DELETE_WINDOW", on_close)

# Function to open the Point Manager window
def open_point_manager():
    global point_manager_window

    # If the window already exists, bring it to the front
    if point_manager_window and point_manager_window.winfo_exists():
        point_manager_window.lift()
        return

    # Create a new "Point Manager" window
    point_manager_window = tk.Toplevel(root)
    point_manager_window.title("Point Manager")
    point_manager_window.geometry("400x400")

    # Function to handle window closing
    def on_close():
        global point_manager_window
        point_manager_window.destroy()
        point_manager_window = None

    # Set the window close protocol
    point_manager_window.protocol("WM_DELETE_WINDOW", on_close)

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

    # Get player ID and name
    player_id, player_name = tree.item(selected_item[0])['values'][0], tree.item(selected_item[0])['values'][1]

    # Show confirmation dialog
    confirm = messagebox.askyesno("Confirm Deletion", f"Are you sure you want to delete {player_name}?")
    if not confirm:
        return  # Cancel the deletion if "No" is selected

    # Proceed with deletion
    cursor.execute("DELETE FROM dkp_table WHERE id = ?", (player_id,))
    connection.commit()
    refresh_display()

    messagebox.showinfo("Success", f"{player_name} has been successfully deleted.")


# GUI setup
root = tk.Tk()
root.title("DKP Calculator")
root.geometry("1800x1000")

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
filter_frame.pack(fill="x")

# Entry widget for filtering by name
filter_entry = tk.Entry(filter_frame)
filter_entry.pack(fill="x", padx=10, pady=5)

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

def filter_treeview(event):
    search_term = filter_entry.get().strip().lower()
    
    # Clear the Treeview
    for item in tree.get_children():
        tree.delete(item)
    
    # Re-insert matching rows
    cursor.execute("""
        SELECT id, name, dkp_base, dkp_gain, dkp_spent, manual_modifire, note, decay_value
        FROM dkp_table
        WHERE LOWER(name) LIKE ?
    """, ('%' + search_term + '%',))
    
    rows = cursor.fetchall()
    for row in rows:
        tree.insert('', 'end', values=row)

# Bind the filter function to the Entry widget
filter_entry.bind("<KeyRelease>", filter_treeview)

# Load and resize the Gorilla Grip image
gorilla_image = Image.open("gorilla_wall.webp")
gorilla_image = gorilla_image.resize((200, 200))
gorilla_photo = ImageTk.PhotoImage(gorilla_image)

gorilla_label = tk.Label(root, image=gorilla_photo)
gorilla_label.place(relx=0.005, rely=0.788)

gorilla_label.image = gorilla_photo

save_to_excel_button = tk.Button(root, text="Save to Excel", command=export_to_excel)
save_to_excel_button.place(relx=0.03, rely=0.70)
# Initial display refresh
refresh_display()

# Run the application
root.mainloop()

# Close the database connection when the app is closed
connection.close()
