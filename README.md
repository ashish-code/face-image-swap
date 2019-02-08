# face-image-swap
Compose image by combining parts of face from a donor image onto a recipient face image. The algorithm uses the facial landmark detection approach of the dlib library to determine image patch that will be extracted from the donor image.

author: Ashish Gupta
email: ashishagupta@gmail.com
version: 0.1.1

----------------------------------------------------------------------
## Usage

Extract the pre-trained facial landmark model file.

usage: 	$python face_swap.py -d <donor-image> -r <recipient-iamge> -o <output-image>
		
options:
"-d", "--donor", dest="donor", help="path to donor face image"
"-r", "--recipient", dest="recipient", help="path to recipient face image"
"-o", "--output", dest="output", default="face_fusion.png", help="path to result image"

----------------------------------------------------------------------
## Requirements

This program uses:
dlib (http://dlib.net/)
opencv (https://github.com/opencv/opencv)

Seek help online on installing these libraries for use with Python 3.x
The installation procedure for these libraries can vary with local system configuration.

------------------------------------------------------------------------

## Results

#### Donor Image:

<img src="https://github.com/ashish-code/face-image-swap/blob/master/ash.jpg" height="400" width="300">

#### Recipient Image:

<img src="https://github.com/ashish-code/face-image-swap/blob/master/trump.jpg" height="400" width="600">

#### Face-swapped Image:

<img src="https://github.com/ashish-code/face-image-swap/blob/master/output.jpg" height="400" width="600">
