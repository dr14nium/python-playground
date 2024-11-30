import json
import psycopg2
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os

CONFIG_FILE = "config.json"

# Fungsi untuk memuat konfigurasi terakhir dari file config.json
def load_last_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {}

# Fungsi untuk menyimpan konfigurasi terakhir ke file config.json
def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f)

# Fungsi untuk mengambil struktur kolom dari GeoJSON
def extract_geojson_structure(geojson_file):
    with open(geojson_file) as f:
        geojson_data = json.load(f)

    first_feature = geojson_data['features'][0]
    properties = first_feature['properties']

    columns = [(key, type(value).__name__) for key, value in properties.items()]
    return columns

# Fungsi untuk membuat tabel dari input UI
def create_table_from_ui(db_config, table_name, column_definitions, geojson_file, status_label):
    try:
        status_label.config(text="Processing...")
        status_label.update()

        conn = psycopg2.connect(
            dbname=db_config['dbname'],
            user=db_config['user'],
            password=db_config['password'],
            host=db_config['host'],
            port=db_config.get('port', 5432)
        )
        cur = conn.cursor()

        column_definitions_str = ", ".join([f'"{col_name}" {col_type}' for col_name, col_type in column_definitions])

        # Definisi tabel dengan MultiPolygonZ
        create_table_query = f"""
            CREATE TABLE IF NOT EXISTS public."{table_name}" (
                id SERIAL PRIMARY KEY,
                geom geometry(MultiPolygonZ, 4326),
                {column_definitions_str}
            );
        """
        cur.execute(create_table_query)
        conn.commit()

        with open(geojson_file) as f:
            geojson_data = json.load(f)

        original_column_names = [col[0] for col in columns]
        renamed_column_names = [col_name for col_name, _ in column_definitions]

        # Loop melalui setiap fitur GeoJSON dan masukkan data
        for feature in geojson_data['features']:
            geom = feature['geometry']
            properties = feature['properties']

            # Konversi geometri ke format 3D jika diperlukan
            if geom['type'] == 'MultiPolygon':
                geom['coordinates'] = [
                    [[coord + [0] if len(coord) == 2 else coord for coord in ring] for ring in polygon]
                    for polygon in geom['coordinates']
                ]

            # Ambil kolom yang tidak dihapus
            column_values = [properties.get(orig_col) for orig_col in original_column_names if orig_col in renamed_column_names]

            # Masukkan data ke tabel
            cur.execute(f"""
                INSERT INTO public."{table_name}" (
                    geom, {", ".join([f'"{col_name}"' for col_name in renamed_column_names])}
                ) VALUES (
                    ST_Force3D(ST_SetSRID(ST_GeomFromGeoJSON(%s::text), 4326)),
                    {", ".join(["%s" for _ in renamed_column_names])}
                )
            """, (
                json.dumps(geom), *column_values
            ))

        conn.commit()
        cur.close()
        conn.close()

        status_label.config(text="Data inserted successfully!")
        messagebox.showinfo("Success", "Data inserted successfully into the database.")
    except Exception as e:
        status_label.config(text="Error occurred!")
        messagebox.showerror("Error", f"An error occurred: {e}")

# Fungsi untuk menghapus tabel
def delete_table(db_config, table_name, status_label):
    try:
        conn = psycopg2.connect(
            dbname=db_config['dbname'],
            user=db_config['user'],
            password=db_config['password'],
            host=db_config['host'],
            port=db_config.get('port', 5432)
        )
        cur = conn.cursor()

        # Drop the table
        drop_table_query = f'DROP TABLE IF EXISTS public."{table_name}";'
        cur.execute(drop_table_query)
        conn.commit()

        cur.close()
        conn.close()

        status_label.config(text="Table deleted successfully!")
        messagebox.showinfo("Success", f"Table '{table_name}' deleted successfully.")
    except Exception as e:
        status_label.config(text="Error occurred!")
        messagebox.showerror("Error", f"An error occurred: {e}")

# UI menggunakan Tkinter untuk input konfigurasi dan modifikasi kolom
def run_ui():
    root = tk.Tk()
    root.title("Load GeoJSON to PostGIS")

    last_config = load_last_config()

    # Label untuk menampilkan status
    status_label = tk.Label(root, text="", fg="blue")
    status_label.pack(pady=10)

    # Fungsi untuk menjalankan pembuatan tabel
    def submit():
        db_config = {
            'dbname': dbname_entry.get(),
            'user': user_entry.get(),
            'password': password_entry.get(),
            'host': host_entry.get(),
            'port': port_entry.get() or 5432
        }

        table_name = table_name_entry.get()

        save_config(db_config)

        column_definitions = []
        for i in range(len(columns)):
            if col_name_entries[i] is not None and col_type_entries[i] is not None:
                col_name = col_name_entries[i].get()
                col_type = col_type_entries[i].get()

                if col_type.startswith("VARCHAR"):
                    if col_length_entries[i] is not None and col_length_entries[i].get():
                        length = col_length_entries[i].get()
                        if length.isdigit() and int(length) <= 10485760:
                            col_type = f"VARCHAR({length})"
                        else:
                            messagebox.showwarning("Invalid Input", f"Invalid length for {col_name}. Maximum length is 10485760.")
                            return
                    else:
                        messagebox.showwarning("Invalid Input", f"Please specify length for {col_name}.")
                        return
                elif col_type.startswith("NUMERIC"):
                    if (col_precision_entries[i] is not None and col_precision_entries[i].get() and
                        col_scale_entries[i] is not None and col_scale_entries[i].get()):
                        precision = col_precision_entries[i].get()
                        scale = col_scale_entries[i].get()
                        if int(precision) <= 1000 and int(scale) <= 1000:
                            col_type = f"NUMERIC({precision}, {scale})"
                        else:
                            messagebox.showwarning("Invalid Input", f"Invalid precision/scale for {col_name}. Maximum is (1000, 1000).")
                            return
                    else:
                        messagebox.showwarning("Invalid Input", f"Please specify precision and scale for {col_name}.")
                        return

                column_definitions.append((col_name, col_type))

        create_table_from_ui(db_config, table_name, column_definitions, geojson_file, status_label)

    # Fungsi untuk memuat GeoJSON dan menampilkan kolom
    def load_geojson():
        global geojson_file, columns, col_name_entries, col_type_entries, col_length_entries, col_precision_entries, col_scale_entries, delete_buttons

        geojson_file = filedialog.askopenfilename(
            title="Select GeoJSON File",
            filetypes=[("GeoJSON files", "*.geojson")]
        )

        if not geojson_file:
            return
        columns = extract_geojson_structure(geojson_file)

        for widget in columns_frame.winfo_children():
            widget.destroy()

        col_name_entries = []
        col_type_entries = []
        col_length_entries = [None] * len(columns)
        col_precision_entries = [None] * len(columns)
        col_scale_entries = [None] * len(columns)
        delete_buttons = []

        for i, (col_name, col_type) in enumerate(columns):
            tk.Label(columns_frame, text=f"Column {i+1}:").grid(row=i, column=0, padx=5, pady=5, sticky='w')
            col_name_entry = tk.Entry(columns_frame)
            col_name_entry.grid(row=i, column=1, padx=5, sticky='w')
            col_name_entry.insert(0, col_name)
            col_name_entries.append(col_name_entry)

            col_type_entry = ttk.Combobox(columns_frame, width=15,
                                          values=["VARCHAR", "TEXT", "INTEGER", "BIGINT", "FLOAT", "DOUBLE PRECISION", "NUMERIC", "BOOLEAN", "DATE", "TIMESTAMP"])
            col_type_entry.grid(row=i, column=2, padx=5, sticky='w')
            col_type_entry.insert(0, col_type_mapping(col_type))
            col_type_entries.append(col_type_entry)

            delete_button = tk.Button(columns_frame, text="Delete", command=lambda idx=i: delete_column(idx))
            delete_button.grid(row=i, column=7, padx=5, pady=5)
            delete_buttons.append(delete_button)

            col_type_entry.bind("<<ComboboxSelected>>", make_show_additional_fields(i))
            make_show_additional_fields(i)()

        root.update_idletasks()
        root.geometry(f"{root.winfo_reqwidth()}x{root.winfo_reqheight()}")

    def delete_column(idx):
        for widget in columns_frame.grid_slaves(row=idx):
            widget.grid_forget()

        col_name_entries[idx] = None
        col_type_entries[idx] = None
        col_length_entries[idx] = None
        col_precision_entries[idx] = None
        col_scale_entries[idx] = None

    def make_show_additional_fields(idx):
        def show_additional_fields(event=None):
            for widget in columns_frame.grid_slaves(row=idx, column=3):
                widget.grid_forget()
            for widget in columns_frame.grid_slaves(row=idx, column=4):
                widget.grid_forget()
            for widget in columns_frame.grid_slaves(row=idx, column=5):
                widget.grid_forget()
            for widget in columns_frame.grid_slaves(row=idx, column=6):
                widget.grid_forget()

            col_length_entries[idx] = None
            col_precision_entries[idx] = None
            col_scale_entries[idx] = None

            if col_type_entries[idx] and col_type_entries[idx].get() == "VARCHAR":
                tk.Label(columns_frame, text="Length:").grid(row=idx, column=3, padx=5, sticky='w')
                col_length_entry = tk.Entry(columns_frame, width=10)
                col_length_entry.grid(row=idx, column=4, padx=5, sticky='w')
                col_length_entries[idx] = col_length_entry
                col_length_entries[idx].insert(0, "255")

            elif col_type_entries[idx] and col_type_entries[idx].get() == "NUMERIC":
                tk.Label(columns_frame, text="Precision:").grid(row=idx, column=3, padx=5, sticky='w')
                col_precision_entry = tk.Entry(columns_frame, width=5)
                col_precision_entry.grid(row=idx, column=4, padx=5, sticky='w')
                col_precision_entries[idx] = col_precision_entry

                tk.Label(columns_frame, text="Scale:").grid(row=idx, column=5, padx=5, sticky='w')
                col_scale_entry = tk.Entry(columns_frame, width=5)
                col_scale_entry.grid(row=idx, column=6, padx=5, sticky='w')
                col_scale_entries[idx] = col_scale_entry
                col_precision_entries[idx].insert(0, "10")
                col_scale_entries[idx].insert(0, "2")

        return show_additional_fields

    def col_type_mapping(py_type):
        if py_type == "str":
            return "VARCHAR"
        elif py_type == "int":
            return "INTEGER"
        elif py_type == "float":
            return "FLOAT"
        else:
            return "VARCHAR"

    config_frame = tk.Frame(root)
    config_frame.pack(pady=10)

    tk.Label(config_frame, text="Database Name").grid(row=0, column=0, padx=5, pady=5, sticky='w')
    dbname_entry = tk.Entry(config_frame)
    dbname_entry.grid(row=0, column=1, padx=5)
    dbname_entry.insert(0, last_config.get('dbname', ''))

    tk.Label(config_frame, text="Username").grid(row=1, column=0, padx=5, pady=5, sticky='w')
    user_entry = tk.Entry(config_frame)
    user_entry.grid(row=1, column=1, padx=5)
    user_entry.insert(0, last_config.get('user', ''))

    tk.Label(config_frame, text="Password").grid(row=2, column=0, padx=5, pady=5, sticky='w')
    password_entry = tk.Entry(config_frame, show="*")
    password_entry.grid(row=2, column=1, padx=5)
    password_entry.insert(0, last_config.get('password', ''))

    tk.Label(config_frame, text="Host").grid(row=3, column=0, padx=5, pady=5, sticky='w')
    host_entry = tk.Entry(config_frame)
    host_entry.grid(row=3, column=1, padx=5)
    host_entry.insert(0, last_config.get('host', 'localhost'))

    tk.Label(config_frame, text="Port").grid(row=4, column=0, padx=5, pady=5, sticky='w')
    port_entry = tk.Entry(config_frame)
    port_entry.grid(row=4, column=1, padx=5)
    port_entry.insert(0, last_config.get('port', '5432'))

    tk.Label(config_frame, text="Table Name").grid(row=5, column=0, padx=5, pady=5, sticky='w')
    table_name_entry = tk.Entry(config_frame)
    table_name_entry.grid(row=5, column=1, padx=5)

    button_frame = tk.Frame(root)
    button_frame.pack(pady=10)

    load_button = tk.Button(button_frame, text="Load GeoJSON", command=load_geojson)
    load_button.grid(row=0, column=0, padx=5)

    submit_button = tk.Button(button_frame, text="Create Table", command=submit)
    submit_button.grid(row=0, column=1, padx=5)

    delete_button = tk.Button(button_frame, text="Delete Table", command=lambda: delete_table({
        'dbname': dbname_entry.get(),
        'user': user_entry.get(),
        'password': password_entry.get(),
        'host': host_entry.get(),
        'port': port_entry.get() or 5432
    }, table_name_entry.get(), status_label))
    delete_button.grid(row=0, column=2, padx=5)

    columns_canvas = tk.Canvas(root)
    columns_canvas.pack(side="left", fill="both", expand=True)

    scrollbar = tk.Scrollbar(root, orient="vertical", command=columns_canvas.yview)
    scrollbar.pack(side="right", fill="y")

    columns_canvas.configure(yscrollcommand=scrollbar.set)
    columns_frame = tk.Frame(columns_canvas)
    columns_canvas.create_window((0, 0), window=columns_frame, anchor="nw")

    def on_frame_configure(event):
        columns_canvas.configure(scrollregion=columns_canvas.bbox("all"))

    columns_frame.bind("<Configure>", on_frame_configure)

    root.mainloop()

if __name__ == "__main__":
    run_ui()