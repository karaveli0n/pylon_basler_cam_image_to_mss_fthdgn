from pypylon import pylon
import datetime
import pyodbc
import tkinter as tk
from tkinter import messagebox, scrolledtext, Toplevel
from PIL import Image, ImageTk
from tkinter import filedialog

debug_list = None
cekim_araligi = 1
conn = None
cursor = None
gerisayim = 0
gerisayim_label = None
timer_running = False
log_dosyasi_yolu = None

def create_db_connection():
    global debug_list  
    try:
        conn = pyodbc.connect('DRIVER={SQL Server};'
                              'SERVER=server_adresi;'
                              'DATABASE=veritabani_adı;'
                              'UID=kullanici_adı;'
                              'PWD=sifre')
        debug_list_insert(f"Veritabanı bağlantısı başarılı. [{datetime.datetime.now():%Y-%m-%d %H:%M:%S}]\n", 'success')
        return conn
    except Exception as e:
        debug_list_insert(f"Veritabanı bağlantı hatası: {str(e)} [{datetime.datetime.now():%Y-%m-%d %H:%M:%S}]\n", 'error')
        open_sql_window()
        return None

def log_yaz(mesaj):
    global log_dosyasi_yolu
    zaman = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_mesaji = f"[{zaman}] {mesaj.strip()}\n"
    
    if log_dosyasi_yolu:
        with open(log_dosyasi_yolu, 'a') as log_dosyasi:
            log_dosyasi.write(log_mesaji)
    else:
        print("Log dosyası seçilmedi, log kaydedilemiyor.")

def debug_list_insert(mesaj, tag=None):
    debug_list.insert(tk.END, mesaj, tag)
    debug_list.see(tk.END)
    log_yaz(mesaj)

def program_baslat():
    debug_list.tag_config('success', foreground='green')
    debug_list.tag_config('error', foreground='red')
    debug_list.tag_config('info', foreground='blue')
    debug_list_insert("Program başlatıldı.\n", 'info')
    if log_dosyasi_yolu is None:
        dosya_konumu_sec()
    
    debug_list_insert("Veritabanına bağlanılıyor...\n", 'info')
    create_db_connection()

    
def goruntu_kaydet(dosya_adi, kamera_adi, parti_no):
    conn = create_db_connection()
    if conn:
        cursor = conn.cursor()
        zaman_damgası = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        tarih_saat = datetime.datetime.now().strftime("%d-%m-%Y %H:%M")
        sutun_adi = f"{tarih_saat} ({kamera_adi})"
        
        sql_sorgu = "INSERT INTO GoruntuTablosu (DosyaAdi, TarihSaat, PartiNo, SutunAdi) VALUES (?, ?, ?, ?)"
        
        cursor.execute(sql_sorgu, (dosya_adi, zaman_damgası, parti_no, sutun_adi))
        conn.commit()
        cursor.close()
        conn.close()
        debug_list_insert(f"Görsel veritabanına kaydedildi: {dosya_adi} [{datetime.datetime.now():%Y-%m-%d %H:%M:%S}]\n", 'success')
    else:
        debug_list_insert(f"Veritabanı bağlantısı sağlanamadı. Görsel kaydedilemedi. [{datetime.datetime.now():%Y-%m-%d %H:%M:%S}]\n", 'error')

def goster(goruntu_yolu, panel):
    try:
        img = Image.open(goruntu_yolu)
        img = img.resize((300, 300), Image.ANTIALIAS)
        img_tk = ImageTk.PhotoImage(img)
        
        panel.config(image=img_tk)
        panel.image = img_tk

        debug_list_insert(f"Görsel başarıyla yüklendi: {goruntu_yolu} [{datetime.datetime.now():%Y-%m-%d %H:%M:%S}]\n", 'success')
    except Exception as e:
        debug_list_insert(f"Görsel yükleme hatası: {str(e)} [{datetime.datetime.now():%Y-%m-%d %H:%M:%S}]\n", 'error')

def onayla():
    global cekim_araligi, gerisayim, timer_running
    program_baslat()
    try:
        cekim_araligi = int(cekim_araligi_entry.get())
        gerisayim = cekim_araligi
        debug_list_insert(f"Çekim aralığı onaylandı: {cekim_araligi} saniye. [{datetime.datetime.now():%Y-%m-%d %H:%M:%S}]\n", 'success')

        if not timer_running:
            timer_running = True
            start_timer()
    except ValueError:
        messagebox.showerror("Geçersiz Girdi", "Lütfen geçerli bir sayı girin.")
        debug_list_insert(f"Geçersiz giriş hatası: Lütfen geçerli bir sayı girin. [{datetime.datetime.now():%Y-%m-%d %H:%M:%S}]\n", 'error')

def start_timer():
    global gerisayim, timer_running
    if timer_running and gerisayim > 0:
        gerisayim_label.config(text=f"Geri Sayım: {gerisayim} saniye", fg="green")
        gerisayim -= 1
        pencere.after(1000, start_timer)
    elif gerisayim == 0:
        gerisayim = int(cekim_araligi_entry.get())
        start_camera_grabbing()
        start_timer()

def stop_timer():
    global timer_running
    timer_running = False
    debug_list_insert(f"Sayaç durduruldu. [{datetime.datetime.now():%Y-%m-%d %H:%M:%S}]\n", 'info')

def resume_timer():
    global timer_running
    if not timer_running:
        timer_running = True
        debug_list_insert(f"Sayaç devam ettirildi. [{datetime.datetime.now():%Y-%m-%d %H:%M:%S}]\n", 'info')
        start_timer()

def start_camera_grabbing():
    global debug_list, parti_no
    tl_factory = pylon.TlFactory.GetInstance()
    devices = tl_factory.EnumerateDevices()

    camera_labels = []
    camera_frame = tk.Frame(pencere)
    camera_frame.pack(side=tk.TOP, anchor='n', pady=5)

    if len(devices) == 0:
        camera_status = "Kameralar bulunamadı."
        camera_label = tk.Label(camera_frame, text=camera_status, fg="red")
        camera_label.pack(side=tk.LEFT, padx=5)
        debug_list_insert(camera_status + f" [{datetime.datetime.now():%Y-%m-%d %H:%M:%S}]\n", 'error')
        return
    else:
        cameras = []
        parti_no = 0  
        current_date = datetime.datetime.now().date()  
        panels = []  
        
        for index, device in enumerate(devices):
            camera = pylon.InstantCamera(device)
            cameras.append(camera)

            try:
                camera.StartGrabbing()
                camera_status = f"{index + 1}. Kamera (aktif) [{datetime.datetime.now():%Y-%m-%d %H:%M:%S}]\n"
                camera_label = tk.Label(camera_frame, text=camera_status, fg="green")
            except Exception:
                camera_status = f"{index + 1}. Kamera (deaktif) [{datetime.datetime.now():%Y-%m-%d %H:%M:%S}]\n"
                camera_label = tk.Label(camera_frame, text=camera_status, fg="red")
            
            camera_label.pack(side=tk.LEFT, padx=5)
            camera_labels.append(camera_label)

            panel = tk.Label(pencere)
            panel.grid(row=0, column=len(panels), padx=5, pady=5)
            panels.append(panel)

        while True:
            today = datetime.datetime.now().date()
            if today != current_date:
                current_date = today
                parti_no = 0  

            for camera_index, camera in enumerate(cameras):
                if camera.IsGrabbing():
                    grab_result = camera.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException)

                    if grab_result.GrabSucceeded():
                        timestamp = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
                        image_filename = f"image_{camera_index + 1}_{timestamp}_parti_{parti_no}.png"
                        pylon.PylonImage().AttachGrabResultBuffer(grab_result).Save(pylon.ImageFileFormat_Png, image_filename)

                        goruntu_kaydet(image_filename, camera_index + 1, parti_no)

                        goster(image_filename, panels[camera_index])

                    grab_result.Release()

            parti_no += 1  
            pencere.after(cekim_araligi * 1000)

    for camera in cameras:
        camera.StopGrabbing()

def kapatma_onayi():
    if messagebox.askyesno("Kapatma Onayı", "Programı kapatmak istediğinize emin misiniz?"):
        pencere.quit()  

def toggle_debug_list():
    if debug_frame.winfo_viewable():
        debug_frame.pack_forget()  
    else:
        debug_frame.pack(side=tk.BOTTOM, fill=tk.X)  
    
def open_sql_window():
    sql_pencere = Toplevel(pencere)
    sql_pencere.title("SQL Server Ayarları")
    sql_pencere.geometry("400x300")

    tk.Label(sql_pencere, text="Server Adresi:").pack(pady=5)
    server_entry = tk.Entry(sql_pencere)
    server_entry.pack(pady=5)

    tk.Label(sql_pencere, text="Veritabanı Adı:").pack(pady=5)
    database_entry = tk.Entry(sql_pencere)
    database_entry.pack(pady=5)

    tk.Label(sql_pencere, text="Kullanıcı Adı:").pack(pady=5)
    uid_entry = tk.Entry(sql_pencere)
    uid_entry.pack(pady=5)

    tk.Label(sql_pencere, text="Şifre:").pack(pady=5)
    pwd_entry = tk.Entry(sql_pencere, show="*")
    pwd_entry.pack(pady=5)

    tk.Button(sql_pencere, text="Kaydet", command=lambda: save_credentials(server_entry.get(), database_entry.get(), uid_entry.get(), pwd_entry.get(), sql_pencere)).pack(pady=10)

def save_credentials(server, database, uid, pwd, sql_pencere):
    connection_string = f"DRIVER={{SQL Server}};SERVER={server};DATABASE={database};UID={uid};PWD={pwd}"
    print("SQL Bağlantı Dizisi:", connection_string)
    create_db_connection()
    sql_pencere.destroy()

def dosya_konumu_sec():
    global log_dosyasi_yolu
    tarih_saat = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    default_filename = f"fırın_{tarih_saat}.txt" 
    log_dosyasi_yolu = filedialog.asksaveasfilename(defaultextension=".txt", 
                                                      filetypes=[("Text files", "*.txt")], 
                                                      initialfile=default_filename) 
    if log_dosyasi_yolu:
        debug_list_insert(f"Log dosyası seçildi: {log_dosyasi_yolu}\n", 'info')
    else:
        debug_list_insert("Log dosyası seçilmedi.\n", 'error')

pencere = tk.Tk()
pencere.title("Kamera Görüntüleri")
pencere.attributes('-fullscreen', True)  

# Üst çerçeve
top_frame = tk.Frame(pencere)
top_frame.pack(side=tk.TOP, fill=tk.X)

cekim_araligi_label = tk.Label(top_frame, text="Çekim Aralığı (saniye): ")
cekim_araligi_label.pack(side=tk.LEFT)

cekim_araligi_entry = tk.Entry(top_frame, width=5)
cekim_araligi_entry.pack(side=tk.LEFT)

cekim_araligi_onayla_btn = tk.Button(top_frame, text="Onayla", command=onayla)
cekim_araligi_onayla_btn.pack(side=tk.LEFT, padx=5)

stop_btn = tk.Button(top_frame, text="Sayaç Durdur", command=stop_timer)
stop_btn.pack(side=tk.LEFT, padx=5)

resume_btn = tk.Button(top_frame, text="Sayaç Devam Ettir", command=resume_timer)
resume_btn.pack(side=tk.LEFT, padx=5)

mss_btn = tk.Button(top_frame, text="Server Ayarları", command=open_sql_window)
mss_btn.pack(side=tk.LEFT, padx=5)

toggle_debug_button = tk.Button(top_frame, text="Debug Listeyi Göster/Gizle", command=toggle_debug_list)
toggle_debug_button.pack(side=tk.LEFT, padx=5)

gerisayim_label = tk.Label(pencere, text="Geri Sayım: 0 saniye", fg="green")
gerisayim_label.pack(side=tk.TOP, anchor='n', pady=10)

debug_frame = tk.Frame(pencere)
debug_frame.pack(side=tk.BOTTOM, fill=tk.X)

debug_list = scrolledtext.ScrolledText(debug_frame, width=60, height=10, wrap=tk.WORD)
debug_list.pack(side=tk.LEFT, padx=5, pady=5)

toplu_kaydet_btn = tk.Button(top_frame, text="Log Dosyası Seç", command=dosya_konumu_sec)
toplu_kaydet_btn.pack(side=tk.LEFT, padx=5)

kapat_btn = tk.Button(top_frame, text="Kapat", command=kapatma_onayi)
kapat_btn.pack(side=tk.RIGHT, padx=5)

pencere.mainloop()
