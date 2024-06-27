import cv2
import numpy as np
from picamera2 import Picamera2
import time
import sys
import threading
import pymysql
import datetime
import qrcode
from tkinter import *
from tkinter import ttk  # Import ttk module
from tkinter import messagebox
from PIL import Image
from PIL import ImageTk
import os
from ultralytics import YOLO


picam = Picamera2()
picam.preview_configuration.main.size = (480, 480)
picam.preview_configuration.main.format = "RGB888"
picam.preview_configuration.main.align()
picam.configure("preview")
picam.start()

model = YOLO("/home/pi/Camera_detect/hx711py-master/runs/detect/train/weights/best.pt")
threshold = 0.5

val = 0
e1 = 0
e2 = 0
e3 = 0
f3=0
f4=0
root=0
label =0
label1 =0
obj_flag = 0
total_list=[]

try:
    con=pymysql.connect(host='192.168.0.141',port=3306,user='root',passwd='root',db='cart',charset='utf8')
    cmd=con.cursor()
    print("Database connected")
    
except Exception as e:
    print(e)
    print("Database not connected")


EMULATE_HX711=False

referenceUnit = 1

if not EMULATE_HX711:
    import RPi.GPIO as GPIO
    GPIO.setwarnings(False)
    from hx711 import HX711
else:
    from emulated_hx711 import HX711

def cleanAndExit():
    print("Cleaning...")

    if not EMULATE_HX711:
        GPIO.cleanup()
        
    print("Bye!")
    sys.exit()

hx = HX711(5, 6)
hx.set_reading_format("MSB", "MSB")
hx.set_reference_unit(-241)
hx.reset()
hx.tare()


def display():
    global f3
    global e1
    global e2
    global e3
    global total_list
    global label
    global root
    global total_list
    global f4
    global label1
    root = Tk()
    root.geometry('1280x720')
    root.title('DIGITAL BILLING')
    root.config(bg="#00008B")
    l1 = Label(root, text="DIGITAL BILLING", font="Helvetica 80 bold", bg="#00008B", fg="white")
    l1.pack()
    l2 = Label(root, text="ITEM", font="Helvetica 15 bold", bg="#00008B", fg="white")
    l2.place(relx=0.15,rely=0.2)
    l3 = Label(root, text="PRICE", font="Helvetica 15 bold", bg="#00008B", fg="white")
    l3.place(relx=0.35,rely=0.2)
    l4 = Label(root, text="QUANTITY", font="Helvetica 15 bold", bg="#00008B", fg="white")
    l4.place(relx=0.15,rely=0.32)
    e1 = Entry(root)
    e1.place(relx=0.15,rely=0.25)
    e2 = Entry(root)
    e2.place(relx=0.35,rely=0.25)
    e3 = Entry(root)
    e3.place(relx=0.15,rely=0.37)
    
#====================================================

    tree_frame = Frame(root, relief=GROOVE, bd=15)
    tree_frame.place(x=850, y=200, width=400, height=300)

    receipt_heading = Label(tree_frame, text="RECEIPT", font="Helvetica 13 bold")
    receipt_heading.pack(pady=5)
    
    tree = ttk.Treeview(tree_frame, columns=("item", "quantity", "price"), show="headings")
    tree.heading("item", text="ITEM")
    tree.heading("quantity", text="QUANTITY (g)")
    tree.heading("price", text="PRICE (₹)")
    tree.column("item", width=110)
    tree.column("quantity", width=100)
    tree.column("price", width=100)
    tree.pack(fill=BOTH)

    f2 = Frame(root, relief=GROOVE, bd=10)
    f2.place(x=850, y=475, width=400, height=50)
    
    t_label = Label(f2, text="TOTAL", font='arial 15 bold', bd=7, relief=GROOVE)
    t_label.pack(side=LEFT)

    total_label = Label(f2, font='arial 15 bold')
    total_label.pack(side=LEFT,padx=40)


    f3 = Frame(root, relief=GROOVE, bd=10)
    f3.place(x=100, y=300, width=320, height=320)

    f4 = Frame(root, relief=GROOVE, bd=8)
    f4.place(x=550, y=230, width=140, height=140)

    label = Label(f3)
    label.pack()

    label1 = Label(f4)
    label1.pack()

#=====================================================
    
    def update_receipt():
        global obj_flag
        item_value = e1.get()
        quantity_value = e3.get()
        price_value = e2.get()
        if item_value and quantity_value and price_value:
            tree.insert("", "end", values=(item_value, quantity_value, price_value))
            update_total()
        else:
            messagebox.showinfo("Alert", "Please show Product infront of camera.")

        e1.delete(0, END)
        e2.delete(0, END)
        e3.delete(0, END)
        obj_flag = 0
        threading.Thread(target=detect).start()
        
    def update_total():
        total_sum = 0
        for item in tree.get_children():
            total_sum += float(tree.item(item, "values")[2])
        total_label.config(text=f"Total: ₹ {total_sum:.2f}")
        
    def update_delete():
        selected_item = tree.selection()
        if selected_item:
            for item in selected_item:
                tree.delete(item)
            update_total()
        else:
            messagebox.showinfo("Alert", "Select an item in the receipt")
        
    def update_clear():
        global total_amount
        tree.delete(*tree.get_children())
        total_label.config(text="")
        total_amount = 0


    def clear_qr_code():
        global label1
        global f4
        #total_label.config(text="")
        for count in range(9,-1,-1):
            print(count)
            label_count=Label(root,text="00:0"+str(count),font="Helvetica 15 bold", bg="#00008B", fg="white")
            label_count.place(x=700, y=250)
            time.sleep(1)
            if count==0:
                f4 = Frame(root, relief=GROOVE, bd=8)
                f4.place(x=550, y=230, width=140, height=140)
                label1 = Label(f4)
                label1.pack()
                break
    
    def generate_upi_qr_code(amount, upi_id):
        global f4
        global label1
        upi_url = f"upi://pay?pa={upi_id}&pn=Recipient Name&mc=&tid=&tr=&tn=&am={amount}&cu=INR"
        
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=3,
            border=1,)
        qr.add_data(upi_url)
        qr.make(fit=True)

        qr_img = qr.make_image(fill_color="black", back_color="white")
        qr_tk = ImageTk.PhotoImage(master=f4, image=qr_img)
        label1.qr_tk = qr_tk
        label1.configure(image=qr_tk)
        threading.Thread(target=clear_qr_code).start()


    def pay():
        global total_amount
        total_amount = total_label.cget("text")
        total_amount = total_amount.split(" ")[-1]  # Extract the numeric part of the total
        print(total_amount)
        upi_id = "shaahidmuhammed052@oksbi"  # Replace with the actual UPI ID
        if total_amount == "0.00":
            messagebox.showinfo("Alert", "Calculate total amount before generating QR code")
        if total_amount == "":
            messagebox.showinfo("Alert", "Calculate total amount before generating QR code")
        else:
            generate_upi_qr_code(total_amount, upi_id)


    b1 = Button(root, text='ADD', font='arial 20 bold', bg="yellow", fg="crimson", command=update_receipt)
    b1.place(x=550, y=400,width=115)
    #b2 = Button(root, text='TOTAL', font='arial 20 bold', bg="yellow", fg="crimson", command=update_total)
    #b2.place(x=550, y=400)
    b3 = Button(root, text='DELETE', font='arial 20 bold', bg="yellow", fg="crimson", command=update_delete)
    b3.place(x=550, y=480)
    b4 = Button(root, text='CLEAR', font='arial 20 bold', bg="yellow", fg="crimson", command=update_clear)
    b4.place(x=550, y=560)
    b4 = Button(root, text='PAY', font='arial 20 bold', bg="yellow", fg="crimson", command=pay)
    b4.place(x=850, y=560)
    root.mainloop()
    
def main():
    threading.Thread(target=display).start()
    threading.Thread(target=detect).start()
    

def detect():
    global root
    global f3
    global label
    global val
    global obj_flag
    frame_height, frame_width = 320, 320 # Specify the frame size
    while obj_flag == 0:

        try:
            val = hx.get_weight(5)
            if val<0:
                val=0
            #print(val)
            hx.power_down()
            hx.power_up()
            time.sleep(0.1)
        except (KeyboardInterrupt, SystemExit):
            cleanAndExit()
        
        img = picam.capture_array()
        #print(ret)
        img = cv2.resize(img, (frame_width, frame_height))
        imga = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        imga = Image.fromarray(imga)
        imgtk = ImageTk.PhotoImage(master=f3, image=imga)
        label.imgtk = imgtk
        label.configure(image=imgtk)
        results = model(img)[0]
        for result in results.boxes.data.tolist():
            x1, y1, x2, y2, score, class_id = result
            if score > threshold:
                cv2.rectangle(img, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 4)
                cv2.putText(img, results.names[int(class_id)].upper(), (int(x1), int(y1 - 10)),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.3, (0, 255, 0), 3, cv2.LINE_AA)
                res = results.names[int(class_id)]
                print(res)
                obj_weight = round(val,2)
                print(obj_weight)
                cmd.execute("select * from price_list where items='" + res + "'")
                r = cmd.fetchone()
                print(r[2])
                if r:
                    price = int(r[2])
                    total_price = round((price * val) / 1000, 2)
                    
                    e1.delete(0, END)
                    e2.delete(0, END)
                    e3.delete(0, END)
                    
                    e1.insert(0, res)
                    e2.insert(0, total_price)
                    e3.insert(0, obj_weight)
                    
                    #obj_flag = 1




if __name__ == "__main__":
    main()
