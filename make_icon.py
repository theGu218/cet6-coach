from PIL import Image, ImageDraw, ImageFont
im = Image.new("RGBA", (256, 256), "#172554")
d = ImageDraw.Draw(im)
d.rounded_rectangle((20, 20, 236, 236), radius=52, fill="#3157C8")
font = ImageFont.truetype(r"C:\Windows\Fonts\segoeuib.ttf", 158)
d.text((128, 118), "6", font=font, fill="white", anchor="mm")
small = ImageFont.truetype(r"C:\Windows\Fonts\segoeuib.ttf", 28)
d.text((128, 204), "CET", font=small, fill="#DCE6FF", anchor="mm")
im.save("CET6Coach.ico", sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])
