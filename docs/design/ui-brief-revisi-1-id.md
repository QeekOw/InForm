# Revisi 1 — apa yang perlu dikerjakan berikutnya

Lanjutan dari `frontend-ui-brief-id.md`. Baca yang itu dulu kalau belum; dokumen ini
tidak mengulang isinya, hanya menambahkan apa yang berubah setelah kami melihat mockup
pertama dan setelah kami mengukur seberapa sering model benar-benar berhasil membaca
lembar InBody asli.

Mockup pertama sudah bagus dan sebagian besar tidak perlu diubah. Yang di bawah ini
bukan daftar kesalahan — sebagian besar adalah hal yang memang belum pernah kami
sampaikan ke kamu.

---

## 0. Mendesak: ganti foto lembar InBody yang asli

Di layar kamera, layar "Analyzing", dan layar Preview, foto yang dipakai adalah lembar
InBody **asli milik orang sungguhan**. Nama gym dan nomor member terbaca jelas di
sana.

Itu data kesehatan pribadi. Mockup nanti masuk ke deck, portfolio, atau README, dan
begitu tersebar tidak bisa ditarik lagi.

**Yang perlu dilakukan:** ganti dengan `real_270_redacted.png` (ada di paket file yang
dikirim bersama dokumen ini — bagian identitasnya sudah dihitamkan), atau dengan lembar
sintetis buatan generator kami. Berlaku juga untuk dua thumbnail di layar pemilihan
270/570.

Ini cepat, tapi tolong dikerjakan lebih dulu sebelum mockup dibagikan ke siapa pun.

---

## 1. Layar "gagal membaca" — ini yang paling penting

Alur di mockup sekarang: Kamera → Analyzing → Preview. Selalu berhasil.

Kenyataannya tidak begitu. Kami baru saja mengukurnya dengan dua belas foto lembar
InBody asli: **enam di antaranya sama sekali tidak terbaca oleh model.** Setengahnya.

Jadi layar yang belum ada itu justru layar yang paling sering dilihat pengguna hari ini.

Ini bukan bug yang akan kami perbaiki lalu hilang. Sistemnya sengaja dirancang begitu:
kalau model tidak yakin, dia **menolak** dan tidak menebak. Lebih baik bilang "tidak
terbaca" daripada memberi angka yang salah lalu menyusun rencana latihan dari angka itu.
Jadi layar ini permanen, bukan sementara.

**Yang perlu didesain:**

- Satu layar untuk kondisi "kami tidak bisa membaca lembar ini".
- Nadanya: **bukan salah pengguna.** Hindari ikon error merah, hindari kesan aplikasi
  rusak atau crash. Ini hasil yang wajar, bukan kegagalan.
- Jelaskan singkat kenapa bisa begitu, dengan bahasa yang bisa ditindaklanjuti —
  misalnya kurang cahaya, ada bayangan, lembar terlipat, foto miring, sebagian terpotong.
- Beri jalan keluar yang jelas. Minimal: foto ulang. Pertimbangkan juga: unggah file
  dari galeri, atau coba dulu pakai lembar contoh supaya pengguna tetap bisa melihat
  aplikasinya bekerja.
- Kalau memungkinkan, hubungkan dengan panduan di layar kamera — pengguna yang gagal
  sekali sebaiknya diberi tahu apa yang harus diperbaiki, bukan disuruh mengulang buta.

Kalau kamu hanya sempat mengerjakan satu hal dari dokumen ini, kerjakan yang ini.

---

## 2. Layar Preview: satu angka tidak sama dengan angka lain

Layar Preview dengan tombol Edit dan Confirm itu ide yang tepat, dan tolong dipertahankan.
Tapi sekarang semua angka ditampilkan dengan bobot visual yang sama persis, seolah semua
sama-sama pasti. Padahal tidak.

Ada tiga kondisi berbeda, dan pengguna harus bisa membedakannya sekilas:

**a. Terbaca bersih.** Model membaca angkanya dan tidak ada yang menyanggah.

**b. Ditandai (flagged).** Model membaca angkanya, tapi pemeriksaan silang kami tidak
setuju. Contoh nyata: di satu lembar, model membaca Lean Body Mass sebagai 30.0 kg,
padahal dari berat badan dan persen lemak seharusnya sekitar 62.5 kg. Angkanya
tetap ditampilkan, tapi pengguna perlu tahu bahwa angka ini **patut dicurigai** dan
sebaiknya dicocokkan dengan lembar aslinya.

**c. Tidak terbaca (unread).** Model tidak menghasilkan apa pun untuk field itu. Kosong.
Pengguna harus mengisinya sendiri, atau memilih melanjutkan tanpa field itu.

Tiga kondisi ini tidak boleh terlihat sama.

**Satu catatan penting soal nada.** Jangan membuat field yang "terbaca bersih" terlihat
seperti sudah **terverifikasi** — jangan centang hijau, jangan label "confirmed". Kami
menemukan kasus di mana model salah baca tapi angkanya tetap masuk akal: lengan kiri dan
kanan yang aslinya 3.53 dan 3.50 terbaca sebagai 3.5 dan 3.7. Tidak ada yang bisa
mendeteksi itu dengan mata, termasuk pemeriksaan silang kami. Kalau tampilannya seolah
sudah dijamin benar, pengguna jadi lebih kecil kemungkinannya mengecek — padahal justru
itu momen di mana kami butuh dia mengecek. Netral lebih baik daripada meyakinkan.

Bagian Segmental Lean Analysis (empat anggota badan) adalah yang paling rawan salah dan
paling tidak terlindungi. Kalau kamu mau memberi penekanan lebih pada satu blok supaya
lebih mengundang untuk diperiksa, blok itu kandidatnya.

---

## 3. Yang sudah bagus dan jangan diubah

Supaya tidak terbuang percuma saat revisi:

- **Pemilihan 270 / 570 sebelum unggah.** Ini bukan sekadar UI yang rapi — ini membantu
  sisi teknis secara langsung, karena model tidak perlu menebak jenis lembarnya. Tolong
  dipertahankan.
- **Panduan di layar kamera** ("pastikan laporan terang, terlihat penuh, mudah dibaca").
  Ini persis intervensi yang menurunkan angka gagal baca di bagian 1.
- **"Continue as Guest".** Sesuai rencana: aplikasi harus bisa dipakai penuh tanpa daftar
  akun dulu.
- **Layar "Analyzing your body composition".** Pembacaan memang makan waktu sekitar 45
  detik, jadi layar ini memang dibutuhkan dan porsinya sudah pas.

---

## 4. Sudah diputuskan, tidak perlu ditanyakan lagi

**Bahasa antarmuka aplikasi: Inggris.** Semua teks yang dilihat pengguna — tombol, label,
pesan error, paragraf tulisan AI — ditulis dalam bahasa Inggris. Dokumen untuk kamu tetap
bahasa Indonesia.

---

## 5. Yang ditunda

Tugas **spesifikasi layout lembar InBody** (`BRIEF-DESAINER-layout-lembar.md`) tetap
berlaku, tapi **turun prioritas** di bawah bagian 1 dan 2 di dokumen ini. Alasannya:
hasil tugas itu baru bisa dipakai setelah kami melatih ulang model, dan pelatihan ulang
itu antre menunggu GPU. Sementara bagian 1 dan 2 memblokir tiga developer sekarang juga.

Satu tugas dari brief itu **dibatalkan**: perbandingan posisi BMI dan Fat Free Mass.
Kami sudah mengujinya sendiri dan dugaannya ternyata salah, jadi tidak perlu kamu lihat.

Kalau nanti tugas layout itu jadi dikerjakan, ada satu tambahan: tolong ukur juga **jarak
dan perataan horizontal antara panel "Segmental Lean Analysis" dan panel "Segmental Fat
Analysis"** yang bersebelahan itu. Kami menemukan model kadang membaca lurus ke kanan
dan menyeberang dari panel kiri ke panel kanan tanpa sadar, jadi hubungan horizontal
antara keduanya ternyata penting.

---

## Urutan yang kami sarankan

1. Ganti foto lembar asli (bagian 0) — cepat, tapi dulukan.
2. Layar gagal membaca (bagian 1).
3. Tiga kondisi field di layar Preview (bagian 2).
4. Layar Result — di mockup masih kosong, dan memang belum kami bahas. Kita bicarakan
   terpisah.
5. Spesifikasi layout lembar (bagian 5), belakangan.

Kalau ada yang tidak jelas atau kelihatannya bertabrakan dengan sesuatu di brief utama,
tanya dulu sebelum dikerjakan — kemungkinan besar itu kesalahan kami menulis, bukan
kesalahan kamu membaca.
