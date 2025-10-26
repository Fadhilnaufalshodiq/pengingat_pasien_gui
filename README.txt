PENGINGAT PASIEN - GUI (Biru Muda) - v2
======================================

Fitur:
- GUI kecil selalu di atas (always on top).
- Pilih interval (menit), default 10 menit.
- Pilih arah awal (KANAN / KIRI).
- Tombol START / STOP dan tombol tes suara.
- Suara: menggunakan pyttsx3 (offline TTS).
- Saat alarm muncul, suara akan diulang selama 30 detik (atau sampai STOP).
- Setelah alarm selesai, timer di-reset dan akan muncul alarm berikutnya bergantian arah.

Cara pakai:
1) Pastikan Python 3 terpasang.
2) Ekstrak folder pengingat_pasien_gui_v2
3) Buka Command Prompt di folder tersebut:
   cd "path\ke\pengingat_pasien_gui_v2"
4) Install dependensi:
   pip install -r requirements.txt
5) Jalankan:
   python main.py

Catatan:
- Jika pyttsx3 tidak bisa bicara pada beberapa mesin, pastikan voice engine Windows SAPI/Microsoft Speech Platform tersedia.
- Untuk run tanpa terminal: kamu bisa buat shortcut yang menjalankan `pythonw main.py`.
