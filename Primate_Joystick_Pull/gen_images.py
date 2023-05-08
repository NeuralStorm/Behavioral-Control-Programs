
from pathlib import Path
from copy import copy
import shutil

from PIL import Image

# img: output of pillow Image
# color: (r, g, b)
def recolor(img, color, *, two_tone=False):
    # img = img.copy()
    # create copy of image and ensure there is an alpha channel
    img = img.convert("RGBA")
    data = img.load()
    
    nr, ng, nb = color
    
    for x in range(img.size[0]):
        for y in range(img.size[1]):
            r, g, b, a = data[x, y]
            
            v = (r + g + b) / 3
            v = 255 - v
            v *= (255/a if a else 0)
            v = int(v)
            
            if two_tone and v > 0:
                v = 255
            
            data[x, y] = (nr, ng, nb, v)
    
    return img

def gen_images():
    CANVAS_SIZE = 1600, 800
    
    # saturation of colors
    SAT = 255 // 2
    
    out_path = Path('./images_gen')
    out_path.mkdir(exist_ok=True)
    src = Path('./TaskImages_Joystick')
    
    prep_path = out_path / 'prepare.png'
    # img = Image.open(src / 'yPrepare.png')
    img = Image.open(src / 'yPrepare_hollow.png')
    img.thumbnail(CANVAS_SIZE)
    # img = recolor(img, (0, SAT, 0))
    img = recolor(img, (114, 114, 114))
    img.save(prep_path, 'PNG')
    
    img = Image.open(src / 'eBlank.png')
    img.thumbnail(CANVAS_SIZE)
    # cimg = recolor(img, (0, SAT, 0), two_tone=True)
    cimg = recolor(img, (57, 255, 20), two_tone=True)
    p = out_path / 'box_green.png'
    cimg.save(p, 'PNG')
    
    cimg = recolor(img, (SAT, 0, 0), two_tone=True)
    p = out_path / 'box_red.png'
    cimg.save(p, 'PNG')
    
    cimg = recolor(img, (SAT, SAT, SAT), two_tone=True)
    p = out_path / 'box_white.png'
    cimg.save(p, 'PNG')
    
    green_dir = out_path / 'green'
    red_dir = out_path / 'red'
    white_dir = out_path / 'white'
    colors = [
        # (green_dir, (0, SAT, 0)),
        (green_dir, (255, 255, 0)),
        (red_dir, (SAT, 0, 0)),
        (white_dir, (SAT, SAT, SAT)),
    ]
    for p, _ in colors:
        p.mkdir(exist_ok=True)
    
    for image_p in src.glob('*.png'):
        c = image_p.stem[0]
        name = image_p.stem
        if c != 'b':
            continue
        print(image_p)
        img = Image.open(image_p)
        img.thumbnail(CANVAS_SIZE)
        for cdir, color in colors:
            cimg = recolor(img, color)
            p = cdir / f"{name}.png"
            cimg.save(p, 'PNG')
    
    yellow_colors = copy(colors)
    yellow_colors[0] = (green_dir, (200, 200, 0))
    
    image_p = src / "bStar.png"
    name = image_p.stem
    img = Image.open(image_p)
    img.thumbnail(CANVAS_SIZE)
    for cdir, color in yellow_colors:
        cimg = recolor(img, color)
        p = cdir / f"{name}_yellow.png"
        cimg.save(p, 'PNG')
    
    img = Image.open(src / 'zmonkey3.jpg')
    # img.thumbnail(CANVAS_SIZE)
    img.thumbnail((430, 400))
    y_offset = 35
    new_image = Image.new('RGBA', (img.width, img.height+y_offset), (0, 0, 0, 0))
    new_image.paste(img, (0, y_offset))
    p = out_path / 'green/monkey3.png'
    # img.save(p, 'PNG')
    new_image.save(p, 'PNG')
    
    img = Image.open(src / 'transparent.png')
    img.thumbnail(CANVAS_SIZE)
    p = out_path / 'red/monkey3.png'
    img.save(p, 'PNG')
    shutil.copyfile(
        out_path / 'red/monkey3.png',
        out_path / 'white/monkey3.png',
    )
    
    # also copy monkey3 transparent image for sun
    shutil.copyfile(
        out_path / 'red/monkey3.png',
        out_path / 'red/sun.png',
    )
    shutil.copyfile(
        out_path / 'red/monkey3.png',
        out_path / 'white/sun.png',
    )
    
    img = Image.open(src / 'sun.png')
    # img.thumbnail(CANVAS_SIZE)
    img.thumbnail((430, 400))
    x_offset = 30
    y_offset = 35
    new_image = Image.new('RGBA', (img.width+x_offset, img.height+y_offset), (0, 0, 0, 0))
    new_image.paste(img, (x_offset, y_offset))
    p = out_path / 'green/sun.png'
    # img.save(p, 'PNG')
    new_image.save(p, 'PNG')
    
    # shutil.copyfile(
    #     out_path / 'red/bRectangle.png',
    #     out_path / 'red/monkey3.png',
    # )
    # shutil.copyfile(
    #     out_path / 'white/bRectangle.png',
    #     out_path / 'white/monkey3.png',
    # )

if __name__ == '__main__':
    gen_images()
