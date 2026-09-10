import codecs

html = """<html xmlns:o='urn:schemas-microsoft-com:office:office' xmlns:w='urn:schemas-microsoft-com:office:word' xmlns='http://www.w3.org/TR/REC-html40'>
<head><title>Surat Keterangan Kerja</title>
<style>
body { font-family: 'Times New Roman', serif; font-size: 11pt; }
table { border-collapse: collapse; width: 100%; margin-top: 10px; margin-bottom: 10px; }
th, td { border: 1px solid black; padding: 4px; text-align: center; }
th { background-color: #f2f2f2; }
.left { text-align: left; }
p { margin: 4px 0; }
</style>
</head>
<body>
<h2 align="center" style="margin-bottom: 5px;">SURAT KETERANGAN KERJA<br/><span style="font-size:11pt;">(PENGANTAR PEMBUKAAN REKENING KOLEKTIF)</span></h2>
<p style="margin-bottom: 12px;"><b>Nomor:</b> ..... / HRD-KGF / VIII / 2026<br/>
<b>Perihal:</b> Pengantar Pembukaan Rekening Karyawan<br/>
<b>Lampiran:</b> 1 (satu) berkas kelengkapan</p>

<p>Kepada Yth.,<br/>
<b>Pimpinan Bank Syariah Indonesia (BSI)</b><br/>
<b>Kantor Cabang Tanjung Karang</b><br/>
Bandar Lampung</p>

<p style="margin-top: 12px;">Dengan hormat,<br/>
Yang bertanda tangan di bawah ini:</p>

<p><b>Nama:</b> Arif Rachman<br/>
<b>Jabatan:</b> Direktur Operasional<br/>
<b>Perusahaan:</b> PT Klumbayan Gold Farm</p>

<p style="margin-top: 10px;">Menerangkan dengan sesungguhnya bahwa nama-nama yang tercantum pada tabel di bawah ini adalah benar <b>karyawan aktif</b> yang bekerja di PT Klumbayan Gold Farm:</p>

<table>
<tr><th>No</th><th>Nama Sesuai KTP</th><th>NIK</th><th>Keperluan</th></tr>
<tr><td>1</td><td class="left">Mamat Sofyan</td><td>3602260202960003</td><td>Pembukaan Rekening</td></tr>
<tr><td>2</td><td class="left">Mahendra Sadepi</td><td>1801080108940011</td><td>Pembukaan Rekening</td></tr>
<tr><td>3</td><td class="left">Nanda Tryas Wicaksana</td><td>1871052105020006</td><td>Pembukaan Rekening</td></tr>
<tr><td>4</td><td class="left">Pitra</td><td>1806181707980002</td><td>Pembukaan Rekening</td></tr>
<tr><td>5</td><td class="left">Yuda Adi Pratama</td><td>1802142808990001</td><td>Pembukaan Rekening</td></tr>
<tr><td>6</td><td class="left">Arif Rahman</td><td>1806181810950001</td><td>Pembukaan Rekening</td></tr>
<tr><td>7</td><td class="left">Asep Hilmansyah, S.Hut</td><td>3204250607880010</td><td>Pembukaan Rekening</td></tr>
<tr><td>8</td><td class="left">Fadillah Nurachman</td><td>1809012910010004</td><td>Pembukaan Rekening</td></tr>
<tr><td>9</td><td class="left">Rahmadi Atma Tristya</td><td>1871130308990004</td><td>Pembukaan Rekening</td></tr>
<tr><td>10</td><td class="left">Fairuz Al Fajri</td><td>3204443008980002</td><td>Pembukaan Rekening</td></tr>
</table>

<p>Surat pengantar ini diterbitkan secara resmi oleh manajemen perusahaan sebagai salah satu syarat kelengkapan administrasi untuk <b>Pembukaan Rekening Tabungan</b> di Bank Syariah Indonesia (BSI) Kantor Cabang Tanjung Karang.</p>

<p style="margin-bottom: 12px;">Demikian surat keterangan kerja ini kami buat dengan sebenarnya agar dapat dipergunakan sebagaimana mestinya oleh pihak Bank Syariah Indonesia. Atas perhatian dan kerja sama yang baik, kami ucapkan terima kasih.</p>

<p>Bandar Lampung, 11 Agustus 2026</p>

<p>Hormat kami,<br/>
<b>PT Klumbayan Gold Farm</b></p>
<br/><br/>
<p><i>(Tanda Tangan & Stempel Perusahaan)</i></p>

<p><b>Arif Rachman</b><br/>
<i>Direktur Operasional</i></p>
</body>
</html>"""

try:
    with codecs.open("/mnt/c/Users/rifra/Downloads/Surat_Keterangan_Kerja_BSI.doc", "w", "utf-8") as f:
        f.write(html)
    print("File .doc berhasil diperbarui!")
except Exception as e:
    print(f"Error: {e}")
