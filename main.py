#!/usr/bin/env python3

import requests
from bs4 import BeautifulSoup, SoupStrainer
from fpdf import FPDF
from PIL import Image
import os
import sys
import shutil
from time import time
from queue import Queue
from threading import Thread


global_image_links = []
global_image_counter = 0


def printProgressBar(iteration, total, prefix='', suffix='', decimals=1, length=100, fill='█'):
    """
    Call in a loop to create terminal progress bar
    @params:
        iteration   - Required  : current iteration (Int)
        total       - Required  : total iterations (Int)
        prefix      - Optional  : prefix string (Str)
        suffix      - Optional  : suffix string (Str)
        decimals    - Optional  : positive number of decimals in percent complete (Int)
        length      - Optional  : character length of bar (Int)
        fill        - Optional  : bar fill character (Str)
    """
    percent = ("{0:." + str(decimals) + "f}").format(100 *
                                                     (iteration / float(total)))
    filledLength = int(length * iteration // total)
    bar = fill * filledLength + '-' * (length - filledLength)
    print('\r%s |%s| %s%% %s' % (prefix, bar, percent, suffix), end='\r')
    # Print New Line on Complete
    if iteration == total:
        print()


def get_image_links(url):
    response = requests.get(url)
    plain_text = response.text
    image_links = []
    for img in BeautifulSoup(plain_text, 'html.parser').findAll('div', {'class': 'img_container'}):
        image_links.append(img.img.get('src'))
    return image_links


def download_image(directory, file_name, link):
    global global_image_counter
    global global_image_links
    download_path = str(directory) + "/" + str(file_name)
    r = requests.get(link)
    with open(str(download_path), "wb") as f:
        f.write(r.content)
    global_image_counter += 1
    printProgressBar(global_image_counter, len(global_image_links),
                     prefix='Progress:', suffix='Complete', length=50)


def create_pdf(directory, output_name):
    i = 1
    num_files = len(os.listdir(directory))
    pdf = FPDF('L','mm','Letter')
    while i <= num_files:
        # See if this is an image that takes up a full page or half page
        image_path = str(directory + "/%s.jpg" % i)
        im = Image.open(image_path)
        width, height = im.size
        pdf.add_page()
        if width > height:
            # Image takes a full page
            # print("Full page image")
            pdf.image(image_path, 0, 0, 279.4, 215.9)
        else:
            # Image is half a page
            # print("Half page image")
            pdf.image(image_path, 279.4/2, 0, 279.4/2, 215.9)
            i += 1
            printProgressBar(i, num_files+1, prefix='Progress:', suffix='Complete', length=50)
            if i > num_files:
                break
            image_path = str(directory + "/%s.jpg" % i)
            pdf.image(image_path, 0, 0, 279.4/2, 215.9)
        i += 1
        printProgressBar(i, num_files+1, prefix='Progress:', suffix='Complete', length=50)
    pdf.output(str(output_name))
    # printProgressBar(num_files+1, num_files+1, prefix='Progress:', suffix='Complete', length=50)


class Image_Download_Worker(Thread):
    def __init__(self, queue):
        Thread.__init__(self)
        self.queue = queue

    def run(self):
        while True:
            directory, file_name, link = self.queue.get()
            try:
                download_image(directory, file_name, link)
            finally:
                self.queue.task_done()


def clearPrevLine():
    sys.stdout.write(u"\u001b[1A") # Move up one line
    sys.stdout.write(u"\u001b[0K") # Clear current line


def single_chapter(url, manga_chapter):
    chapter = input("Select Chapter: ")
    while int(chapter) <= 0:
        clearPrevLine()
        chapter = input(u"\u001b[1000D" + "Chapter must be positive. Select Chapter: ")
    clearPrevLine()
    try:
        download_chapter(url, manga_chapter, chapter)
    except Exception as e:
        print(e)


def range_chapter(url, manga_chapter):
    # Input range
    range_start = input("Start Range: ")
    while int(range_start) <= 0:
        clearPrevLine()
        range_start = input(u"\u001b[1000D" + "Start Range must be positive. Select Start Range: ")
    range_end = input("End Range: ")
    while int(range_end) <= 0 and int(range_end) <= int(range_start):
        clearPrevLine()
        range_end = input(u"\u001b[1000D" + "End Range must be positive and greater than Start Range. Select End Range: ")
    clearPrevLine()
    clearPrevLine()
    count = 0
    for chapter in range(int(range_start), int(range_end) + 1):
        print("[%d/%d]" % (count, int(range_end) - int(range_start)))
        try:
            download_chapter(url, manga_chapter, chapter)
        except Exception as e:
            print("Error completing chapter")
            print(e)
        # Update Range Counter
        # clearPrevLine()
        count += 1
        clearPrevLine()


def download_chapter(url, manga_chapter, chapter):
    global global_image_links
    global global_image_counter

    url = url + str(chapter)
    manga_chapter = manga_chapter + str(chapter)
    print(url)
    print(manga_chapter)

    if not os.path.exists(manga_chapter):
        os.mkdir(manga_chapter)

    print("[Get Image Links]")
    global_image_links = get_image_links(url)
    print("[Obtained Image Links]")
    print("Downloading Images")
    global_image_counter = 0

    image_queue = Queue()
    for t in range(10):
        worker = Image_Download_Worker(image_queue)
        worker.daemon = True
        worker.start()
    for i, link in enumerate(global_image_links):
        image_queue.put((manga_chapter, "%s.jpg" % (i+1), link))
    image_queue.join()

    print("[Finished Downloading]")

    print("[Create PDF]")
    create_pdf(manga_chapter, str(manga_chapter + ".pdf"))
    print("[Finished Creating PDF]")
    shutil.rmtree(manga_chapter)

    for i in range(10):
        clearPrevLine()


# TODO: Separate Choice logic to separate functions (clean up main())
# TODO: Add in functionality to see how many available chapters there are

def main(argv):
    global global_image_links
    global global_image_counter

    # Display instructions:
    print("Select Manga:")
    print("[1] One Punch Man")
    print("[2] Hunter x Hunter")
    choice = input("Choice: ")
    while int(choice) is not 1 and int(choice) is not 2:
        clearPrevLine()
        choice = input(u"\u001b[1000D" + "Please select 1 or 2: ")
    for i in range(4):
        clearPrevLine()
    url = ""
    manga_chapter = ""
    manga = ""
    if int(choice) is 1:
        manga = "[One Punch Man]"
        print(manga)
        url = "http://readonepunchman.net/manga/onepunch-man-chapter-"
        manga_chapter = "onepunch-man-chapter-"
    if int(choice) is 2:
        manga = "[Hunter x Hunter]"
        print(manga)
        url = "http://readhunterxhunter.net/manga/hunter-x-hunter-chapter-"
        manga_chapter = "hunter-x-hunter-chapter-"

    print("[1] Single Chapter")
    print("[2] Range")
    choice = input("Choice: ")
    while int(choice) is not 1 and int(choice) is not 2:
        clearPrevLine()
        choice = input(u"\u001b[1000D" + "Please select 1 or 2: ")
    for i in range(3):
        clearPrevLine()


    if not os.path.exists(manga):
        os.mkdir(manga)
    os.chdir(manga)

    ts = time()

    if int(choice) is 1:
        single_chapter(url, manga_chapter)
    if int(choice) is 2:
        range_chapter(url, manga_chapter)



    print("[Total exec time: " + str(time() - ts) + "]")




if __name__ == "__main__":
    main(sys.argv[1:])
