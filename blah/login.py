from tkinter import*
from tkinter import ttk
from PIL import Image,ImageTk
from tkinter import messagebox


class Login_Window:
    def __init__(self,root):
        self.root=root
        self.root.title("Login")
        self.root.geometry("1500x800+0+0")

        self.bg=ImageTk.PhotoImage(file=r"C:\Users\HP\Desktop\FaceProject\Image\lib.jpg")

        lbl_bg=Label(self.root,image=self.bg)
        lbl_bg.place(x=0,y=0,relwidth=1,relheight=1)

        frame=Frame(self.root,bg="White")
        frame.place(x=610,y=170,width=340,height=450)

        img1=Image.open(r"C:\Users\HP\Desktop\FaceProject\Image\login.png")
        img1=img1.resize((130,130),Image.Resampling.LANCZOS)




        self.photoimage1=ImageTk.PhotoImage(img1)
        lblimg1=Label(image=self.photoimage1,bg="white",borderwidth=0)
        lblimg1.place(x=730,y=175,width=100,height=100)

        get_str=Label(frame,text="Get Started",font=("Times new roman",20,"bold"),fg="dark Blue",bg="White")
        get_str.place(x=95,y=100)

        #Labelllllll
        username=lbl=Label(frame,text="Username",font=("Times new roman",15,"bold"),fg="Black",bg="White")
        username.place(x=65,y=155)

        self.txtuser=ttk.Entry(frame,font=("Times new roman",15,"bold"))
        self.txtuser.place(x=40,y=180,width=270)

        password=lbl=Label(frame,text="Password",font=("Times new roman",15,"bold"),fg="Black",bg="White")
        password.place(x=65,y=225)

        self.txtpass=ttk.Entry(frame,font=("Times new roman",15,"bold"))
        self.txtpass.place(x=40,y=250,width=270)


    #===========icon images===============
        img2=Image.open(r"C:\Users\HP\Desktop\FaceProject\Image\user-png.png")
        img2=img2.resize((25,25),Image.Resampling.LANCZOS)
        self.photoimage2=ImageTk.PhotoImage(img2)
        lblimg2=Label(image=self.photoimage2,bg="white",borderwidth=0)
        lblimg2.place(x=650,y=323,width=25,height=25)

        img3=Image.open(r"C:\Users\HP\Desktop\FaceProject\Image\pass.png")
        img3=img3.resize((25,25),Image.Resampling.LANCZOS)
        self.photoimage3=ImageTk.PhotoImage(img3)
        lblimg3=Label(image=self.photoimage3,bg="white",borderwidth=0)
        lblimg3.place(x=650,y=397,width=25,height=25)
#BUTTON
        loginbtn=Button(frame,text="Login",font=("Times new roman",15,"bold"),command=self.login,bd=3,relief=RIDGE,fg="white",bg="red",activeforeground="white",activebackground="red")
        loginbtn.place(x=110,y=305,width=120,height=35)
    # register button
        registerbtn=Button(frame,text="New User Register",font=("Times new roman",10,"bold"),borderwidth=0,fg="black",bg="white",activeforeground="white",activebackground="white")
        registerbtn.place(x=15,y=350,width=160)
    #Forget password button
        passwordbtn=Button(frame,text="Forget Password",font=("Times new roman",10,"bold"),borderwidth=0,fg="black",bg="white",activeforeground="white",activebackground="white")
        passwordbtn.place(x=10,y=370,width=160)

    def login(self):
        if self.txtuser.get()=="" or self.txtpass.get()=="":
            messagebox.showerror("Error!","All fields are required")
        elif self.txtuser.get()=="harshu" and self.txtpass.get()=="arshu":
            messagebox.showinfo("Success!","Welcome to our page!!")
        else:
            messagebox.showerror("Invalid","Invalid username or password")

if __name__=="__main__":
    root=Tk()
    app=Login_Window(root)
    root.mainloop()
