import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import struct

# Configurações
offset_base = 0x35C
entry_size = 0x10
entry_format = '<HbbBBBBHHHH'
fields_order = [
    'texture_id', 'x_shift', 'y_shift', 'width', 'height', 'spacing', 'unused7',
    'u0', 'u1', 'v1', 'v0'
]
font_image_path = "font.png"
input_file = "font.bin"
output_file = "font_new.bin"

# Mapeamento manual (offsets reais)
manual_offset_map = {
    0x30E0: 0x0D4C,   # ム
    0x30E1: 0x14EC,   #0x22AC
    0x30E2: 0x14FC,   # モ
    0x30E8: 0x155C,   # ヨ
    0x30EA: 0x157C,    
    0x30EB: 0x158C, 
    0x30EC: 0x159C,
    0x30ED: 0x15AC,
    0x30EF: 0x15CC, 
    0x30F3: 0x15EC, 
    0x4E0A: 0x0B9E, 
    0x4E86: 0x17DC,
    0x4E88: 0x17EC,
    0x4E92: 0x183C,
    0x4E9C: 0x185C,#
    0x5320: 0x22AC,
    0x5339: 0x22BC,
    0x533A: 0x22CC,
}

# Carrega imagem da fonte
glyph_img = Image.open(font_image_path).convert("RGBA")

# Lê dados binários
with open(input_file, "rb") as f:
    font_data = bytearray(f.read())

# Lê todas as entradas
entries = []
offset_to_entry = {}
num_entries = (len(font_data) - offset_base) // entry_size
for i in range(num_entries):
    offset = offset_base + i * entry_size
    chunk = font_data[offset:offset + entry_size]
    if len(chunk) == entry_size:
        unpacked = struct.unpack(entry_format, chunk)
        entry = dict(zip(fields_order, unpacked))
        entry['index'] = i
        entry['offset'] = offset
        entries.append(entry)
        offset_to_entry[offset] = entry

# Inicialização do mapeamento
ascii_start_offset = offset_base
ascii_start_code = 0x20
ascii_end_index = 94
japanese_base_offset = offset_base + 95 * entry_size
japanese_base_unicode = 0x30A0

unicode_to_index = {}
used_offsets = set()

# Mapeia offsets manuais
for unicode_val, real_offset in manual_offset_map.items():
    if real_offset not in offset_to_entry:
        chunk = font_data[real_offset:real_offset + entry_size]
        if len(chunk) == entry_size:
            unpacked = struct.unpack(entry_format, chunk)
            entry = dict(zip(fields_order, unpacked))
            entry['index'] = len(entries)
            entry['offset'] = real_offset
            entries.append(entry)
            offset_to_entry[real_offset] = entry
    entry = offset_to_entry[real_offset]
    entry['char'] = chr(unicode_val)
    unicode_to_index[unicode_val] = entry['index']
    used_offsets.add(real_offset)

# Mapeia automaticamente os demais (sem sobrescrever os manuais)
for entry in entries:
    if entry['offset'] in used_offsets:
        continue
    try:
        if entry['index'] <= ascii_end_index:
            unicode_val = ascii_start_code + (entry['offset'] - ascii_start_offset) // entry_size
        else:
            unicode_val = japanese_base_unicode + (entry['offset'] - japanese_base_offset) // entry_size
        if unicode_val not in unicode_to_index:
            entry['char'] = chr(unicode_val)
            unicode_to_index[unicode_val] = entry['index']
    except:
        entry['char'] = f"U+{unicode_val:04X}"

# GUI
root = tk.Tk()
root.title("Digimon REditor de Fonte VWF (PSP) Developed By Sora Leon")
root.geometry("640x700")

selected_index = tk.IntVar(value=0)
char_label = tk.StringVar()
offset_label = tk.StringVar()
search_char = tk.StringVar()
fields = {}
status = tk.StringVar(value="Pronto")

preview_canvas = tk.Canvas(root, width=64, height=64)

def update_ui():
    idx = selected_index.get()
    if 0 <= idx < len(entries):
        e = entries[idx]
        char_label.set(f"Caractere: {e.get('char', '?')}")
        offset_label.set(f"Offset: 0x{e['offset']:X}")
        for f in fields_order:
            fields[f].delete(0, tk.END)
            fields[f].insert(0, str(e[f]))
        draw_preview(e)

def draw_preview(e):
    try:
        u0, u1, v1, v0 = e['u0'], e['u1'], e['v1'], e['v0']
        if u1 <= u0 or v1 <= v0:
            raise ValueError("Coordenadas inválidas")
        glyph = glyph_img.crop((u0, v0, u1, v1)).resize((64, 64))
    except Exception:
        glyph = Image.new("RGBA", (64, 64), (128, 0, 0, 255))
    img = ImageTk.PhotoImage(glyph)
    preview_canvas.image = img
    preview_canvas.delete("all")
    preview_canvas.create_image(0, 0, anchor='nw', image=img)

def save_entry():
    idx = selected_index.get()
    if 0 <= idx < len(entries):
        try:
            vals = [int(fields[f].get()) for f in fields_order]
            packed = struct.pack(entry_format, *vals)
            offset = entries[idx]['offset']
            font_data[offset:offset + entry_size] = packed
            for f, v in zip(fields_order, vals):
                entries[idx][f] = v
            status.set(f"Entrada {idx} salva.")
            update_ui()
        except Exception as e:
            messagebox.showerror("Erro ao salvar", str(e))
            status.set("Erro ao salvar entrada.")

def save_file():
    with open(output_file, "wb") as f:
        f.write(font_data)
    status.set(f"Arquivo salvo como '{output_file}'")

def search():
    target = search_char.get()
    if not target:
        return
    try:
        code = ord(target[0]) if not target.startswith("U+") else int(target[2:], 16)
    except Exception:
        messagebox.showerror("Erro", "Código Unicode inválido")
        return

    if code in unicode_to_index:
        idx = unicode_to_index[code]
        selected_index.set(idx)
        update_ui()
    else:
        messagebox.showwarning("Busca", f"Caractere U+{code:04X} não encontrado no mapeamento.")

# Layout
frame = ttk.Frame(root)
frame.pack(padx=10, pady=10, fill='both', expand=True)

ctrls = ttk.Frame(frame)
ctrls.pack(fill='x', pady=5)
ttk.Label(ctrls, text="Índice:").pack(side='left')
ttk.Spinbox(ctrls, from_=0, to=len(entries)-1, textvariable=selected_index, width=6, command=update_ui).pack(side='left')
ttk.Button(ctrls, text="Carregar", command=update_ui).pack(side='left', padx=4)
ttk.Button(ctrls, text="Salvar Entrada", command=save_entry).pack(side='left', padx=4)
ttk.Button(ctrls, text="Salvar Arquivo", command=save_file).pack(side='left', padx=4)

info = ttk.Frame(frame)
info.pack(fill='x', pady=5)
ttk.Label(info, textvariable=char_label, font=("Arial", 12, "bold")).pack()
ttk.Label(info, textvariable=offset_label).pack()

search_frame = ttk.Frame(frame)
search_frame.pack(pady=5)
ttk.Label(search_frame, text="Buscar caractere:").pack(side='left')
ttk.Entry(search_frame, textvariable=search_char, width=8).pack(side='left')
ttk.Button(search_frame, text="Buscar", command=search).pack(side='left')

fields_frame = ttk.Frame(frame)
fields_frame.pack(pady=5, fill='x')
for i, name in enumerate(fields_order):
    ttk.Label(fields_frame, text=name).grid(row=i, column=0, sticky='e')
    entry = ttk.Entry(fields_frame)
    entry.grid(row=i, column=1, sticky='we')
    fields[name] = entry

preview_canvas.pack(pady=10)

statusbar = ttk.Label(root, textvariable=status, relief='sunken', anchor='w')
statusbar.pack(fill='x', side='bottom')

update_ui()
root.mainloop()
