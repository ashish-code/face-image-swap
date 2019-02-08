# face-image-swap
Compose image by combining parts of face from a donor image onto a recipient face image. The algorithm uses the facial landmark detection approach of the dlib library to determine image patch that will be extracted from the donor image.

author: Ashish Gupta
email: ashishagupta@gmail.com
version: 0.1.1

----------------------------------------------------------------------

usage: 	$python face_swap.py
		$python pGan_fSplice.py [option] arg
		
options:
"-d", "--donor", dest="donor", help="path to donor face image"
"-r", "--recipient", dest="recipient", help="path to recipient face image"
"-o", "--output", dest="output", default="face_fusion.png", help="path to result image"

----------------------------------------------------------------------

Requirements:
This program uses:
dlib (http://dlib.net/)
opencv (https://github.com/opencv/opencv)

Seek help online on installing these libraries for use with Python 3.x
The installation procedure for these libraries can vary with local system configuration.

----------------------------------------------------------------------

output file naming convention:
The resulting file is named as: <donor image name>--<recipient image name>.png
You can use the '--' to split the result file name to acquire the donor/recipient image name and change it as desired.

The program is not designed to work in all circumstances, ie. face not detected or sufficient facial landmarks not found,
for the face path is too small, etc. In all such cases, the failed output file is recorded in a log file: ./log.txt
