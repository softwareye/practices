#coding:utf-8
"""
photomosaic.py

从给定的目标图像和存放小块图像的文件夹创建照片马赛克

作者: Mahesh Venkitachalam
"""

import sys, os, random, argparse
from PIL import Image
import imghdr
import numpy as np

def getAverageRGBOld(image):
  """
  计算并返回给定 Image 对象 (r,g,b) 形式的颜色平均值,
  此函数已废弃
  """
  # no. of pixels in image
  npixels = image.size[0]*image.size[1]
  # get colors as [(cnt1, (r1, g1, b1)), ...]
  cols = image.getcolors(npixels)
  # get [(c1*r1, c1*g1, c1*g2),...]
  sumRGB = [(x[0]*x[1][0], x[0]*x[1][1], x[0]*x[1][2]) for x in cols] 
  # calculate (sum(ci*ri)/np, sum(ci*gi)/np, sum(ci*bi)/np)
  # the zip gives us [(c1*r1, c2*r2, ..), (c1*g1, c1*g2,...)...]
  avg = tuple([int(sum(x)/npixels) for x in zip(*sumRGB)])
  return avg

def getAverageRGB(image):
  """
  计算并返回给定 Image 对象 (r,g,b) 形式的颜色平均值
  """
  # 将图像转换成 numpy 中的数组
  im = np.array(image)
  # 获取数组的长, 宽, 高
  w,h,d = im.shape
  # 计算均值
  return tuple(np.average(im.reshape(w*h, d), axis=0))

def splitImage(image, size):
  """
  根据给定图像的维度来分割图像，返回一个大小为  m*n 的图像列表
  """
  W, H = image.size[0], image.size[1]
  m, n = size
  w, h = int(W/n), int(H/m)
  # 图像列表
  imgs = []
  # 生成列表
  for j in range(m):
    for i in range(n):
      # 向 imgs 中追加裁减后的小块图像
      imgs.append(image.crop((i*w, j*h, (i+1)*w, (j+1)*h)))
  return imgs


def getImages(imageDir):
  """
  给定一个目录，加载该目录下的图像，并以列表的形式返回
  """
  files = os.listdir(imageDir)
  images = []
  for file in files:
    filePath = os.path.abspath(os.path.join(imageDir, file))
    try:
      # 显式加载以避免资源危机
      fp = open(filePath, "rb")
      im = Image.open(fp)
      images.append(im)
      # 强制从文件中加载图像数据
      im.load() 
      # 关闭文件
      fp.close() 
    except:
      # skip
      print("Invalid image: %s" % (filePath,))
  return images

def getImageFilenames(imageDir):
  """
  返回指定目录所有的图像文件名
  """
  files = os.listdir(imageDir)
  filenames = []
  for file in files:
    filePath = os.path.abspath(os.path.join(imageDir, file))
    try:
      imgType = imghdr.what(filePath) 
      if imgType:
        filenames.append(filePath)
    except:
      # 跳过
      print("Invalid image: %s" % (filePath,))
  return filenames


def getBestMatchIndex(input_avg, avgs):
  """
  返回按照 RGB 值的距离挑选出的最佳匹配。
  """
  # 图像的均值
  avg = input_avg

  # 根据 x/y/z 的距离从 avgs 中挑选出距 input_avg 最近的值
  index = 0
  min_index = 0
  min_dist = float("inf")
  for val in avgs:
    dist = ((val[0] - avg[0])*(val[0] - avg[0]) +
            (val[1] - avg[1])*(val[1] - avg[1]) +
            (val[2] - avg[2])*(val[2] - avg[2]))
    if dist < min_dist:
      min_dist = dist
      min_index = index
    index += 1

  return min_index


def createImageGrid(images, dims):
  """
  Given a list of images and a grid size (m, n), create 
  a grid of images. 
  """
  m, n = dims

  # 检查参数
  assert m*n == len(images)

  # 统计小块图像宽度和高度的最大值
  # 没有假设所有小块图像的大小都是统一的
  width = max([img.size[0] for img in images])
  height = max([img.size[1] for img in images])

  # 创建输出图像
  grid_img = Image.new('RGB', (n*width, m*height))

  # 粘贴图像
  for index in range(len(images)):
    row = int(index/n)
    col = index - n*row
    grid_img.paste(images[index], (col*width, row*height))

  return grid_img


def createPhotomosaic(target_image, input_images, grid_size,
                      reuse_images=True):
  """
  从给定的目标图像和小块图像创建照片马赛克
  """

  print('splitting input image...')
  # 将目标图像分割分割成子图像
  target_images = splitImage(target_image, grid_size)

  print('finding image matches...')
  # 对于每一个目标图像，从输入选择一个
  output_images = []
  # 用于向用户反馈
  count = 0
  batch_size = int(len(target_images)/10)

  # 计算输入的小块图像的平均值
  avgs = []
  for img in input_images:
    avgs.append(getAverageRGB(img))

  for img in target_images:
    # 计算子图像的均值
    avg = getAverageRGB(img)
    # 寻找最匹配的索引
    match_index = getBestMatchIndex(avg, avgs)
    output_images.append(input_images[match_index])
    # 向用户反馈进度
    if count > 0 and batch_size > 10 and count % batch_size is 0:
      print('processed %d of %d...' %(count, len(target_images)))
    count += 1
    # 如果不允许重用图像, 就移除被选中的图像
    if not reuse_images:
      input_images.remove(match_index)

  print('creating mosaic...')
  # 将照片马赛克保存在图像中
  mosaic_image = createImageGrid(output_images, grid_size)

  # 返回照片马赛克
  return mosaic_image

# 在 main() 函数中调用我们的代码, 实现照片马赛克
def main():
  # 命令行参数保存在 sys.argv[1], sys.argv[2] .. 中
  # sys.argv[0] 是可被忽略的脚本名字

  # 解析命令行参数
  parser = argparse.ArgumentParser(description='Creates a photomosaic from input images')
  # 添加命令行参数
  parser.add_argument('--target-image', dest='target_image', required=True)
  parser.add_argument('--input-folder', dest='input_folder', required=True)
  parser.add_argument('--grid-size', nargs=2, dest='grid_size', required=True)
  parser.add_argument('--output-file', dest='outfile', required=False)

  args = parser.parse_args()

  ###### INPUTS ######

  # 载入目标图像
  target_image = Image.open(args.target_image)

  # 从目录下读入小块图像
  print('reading input folder...')
  input_images = getImages(args.input_folder)

  # 判断小块图像列表是否为空
  if input_images == []:
      print('No input images found in %s. Exiting.' % (args.input_folder, ))
      exit()

  # 是否使用随机列表 - 来增加输出的多样性?
  random.shuffle(input_images)

  # 网格的大小
  grid_size = (int(args.grid_size[0]), int(args.grid_size[1]))

  # 输出文件名
  output_filename = 'mosaic.png'
  if args.outfile:
    output_filename = args.outfile

  # 是否允许重用输入的图片
  reuse_images = True

  # 是否调整输入图片的大小来适应网格
  resize_input = True

  ##### 结束输入 #####

  print('starting photomosaic creation...')

  # 如果不能重复利用图片, 验证 m*n <= num_of_images 是否成立
  if not reuse_images:
    if grid_size[0]*grid_size[1] > len(input_images):
      print('grid size less than number of images')
      exit()

  # 重新调整输入图片的大小
  if resize_input:
    print('resizing images...')
    # 根据给定的网格大小，统计宽度和高度的最大值
    dims = (int(target_image.size[0]/grid_size[1]), 
            int(target_image.size[1]/grid_size[0])) 
    print("max tile dims: %s" % (dims,))
    # 调整图片大小
    for img in input_images:
      img.thumbnail(dims)

  # 创建照片马赛克
  mosaic_image = createPhotomosaic(target_image, input_images, grid_size,
                                   reuse_images)

  # 保存 mosaic 到文件
  mosaic_image.save(output_filename, 'PNG')

  print("saved output to %s" % (output_filename,))
  print('done.')

# 调用 main() 函数执行程序的标准样板
if __name__ == '__main__':
  main()
