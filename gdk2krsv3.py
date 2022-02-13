"""
Script Program Transformasi Koordinat Geodetik ke Kartesi
author  :dr14nium
date    :31 August 2021
"""

import math

#Konversi Derajat Menit Detik ke Derajat Desimal
def dms2dd(derajat, menit, detik, lokasi):
    dd = float(derajat) + float(menit)/60 + float(detik)/(60*60);
    if lokasi == 'B' or lokasi == 'S':
        dd *= -1
    return dd;


#Transformasi Koordinat Titik dari Geodetik ke Kartesian
def gdk2krs(lintang, bujur):
    #Konversi Satuan Sudut DD ke Radians
    lintang = math.radians(lintang)
    bujur = math.radians(bujur)

    #Menghitung Eksintrisitas Pertama Ellipsoid Acuan (e) dan Jari-Jari Kelengkungan Vertikal Utama (N)
    e = math.sqrt((a**2-b**2)/(a**2))
    N = a / math.sqrt(1 - e**2 * math.sin(lintang)**2)

    #Menghitung Koordinat X, Y, dan Z
    X = N * math.cos(lintang) * math.cos(bujur)
    Y = N * math.cos(lintang) * math.sin(bujur)
    Z = N * (1 - e**2) * math.sin(lintang)

    return round(X,3), round(Y,3), round(Z,3)

#Ellipsoid Referensi
def WGS84 ():
    print("Ellipsoid Acuan WGS 1984")
    a = float(6378137)
    f = float(1/298.257223563)
    b = a*(1-f)

    return a, b

def GRS67 ():
    print("Ellipsoid Acuan GRS 1967")
    a = float(6378160)
    f = float(1/298.247)
    b = a*(1-f)

    return a, b

def DS ():
    print("Ellipsoid Acuan DS")
    a = float(6378468.84)
    f = float(1/298.488)
    b = a*(1-f)

    return a, b

#Input Lintang
def inlat ():
    derajat = input('Derajat                :')
    menit = input('Menit                  :')
    detik = input('Detik                  :')
    lokasi = input('Letak Lintang (U/S)    :')
    lintang = dms2dd(derajat, menit, detik, lokasi)

    return lintang

#Input Bujur
def inlong ():
    derajat = input('Derajat                :')
    menit = input('Menit                  :')
    detik = input('Detik                  :')
    lokasi = input('Letak Bujur (B/T)       :')
    bujur = dms2dd(derajat, menit, detik, lokasi)
    
    return bujur
        

#Main Program
print('Pilih Ellipsoid Referensi yang digunakan ketikkan angka sesuai pilihan (1/2/3)\n 1. WGS 1984\n 2. GRS 1967\n 3. DS ')

inref = int(input('Elipsoid yang dipilih: '))

print("\n")
if(inref == 1):
    a,b = WGS84()
elif(inref == 2):
    a,b = GRS67()
elif(inref == 3):
    a,b = DS()

print("Nilai a = ", a)
print("Nilai b = ", b)

point = int(input('Masukkan jumlah titik yang akan dikonversi : '))

i = 0
n = 0
j = 0
titik = []

while (i < point):
    i += 1
    n += 1
    
    if (i == n):
        print("\n")
        print('Nilai Lintang Titik ', i)
        lintang = inlat()

        print("\n")
        print('Nilai Bujur Titik ', i)
        bujur = inlong()

        calc = gdk2krs(lintang, bujur)
        titik.append(calc)
   

print("\n")
print("Hasil Transformasi Koordinat Geodetik ke Kartesian (X,Y,Z)")

for i in titik:
    j += 1
    print("Titik",j, " = ", i)

print("\n")
