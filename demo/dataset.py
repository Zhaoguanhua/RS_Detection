#!usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Author  : zhaoguanhua
@Email   : 
@Time    : 2021/5/17 21:16
@File    : dataset.py
@Software: PyCharm
"""
import os
import torch
import torch.utils.data
import cv2
import json
import numpy as np
from pycocotools import mask as coco_mask
from utils_tool import transforms as T
from PIL import Image

class PennFudanDataset(torch.utils.data.Dataset):
    def __init__(self, root, transforms=None):
        self.root = root
        self.transform = transforms
        self.imgs = list(sorted(os.listdir(os.path.join(root, "PNGImages"))))
        self.masks = list(sorted(os.listdir(os.path.join(root, "PedMasks"))))

    def __getitem__(self, idx):
        # load images ad masks
        img_path = os.path.join(self.root, "PNGImages", self.imgs[idx])
        mask_path = os.path.join(self.root, "PedMasks", self.masks[idx])

        img = Image.open(img_path)
        img = img.convert("RGB")
        mask = Image.open(mask_path)
        mask = np.array(mask)

        obj_ids = np.unique(mask)
        obj_ids = obj_ids[1:]

        masks = mask == obj_ids[:, None, None]

        num_objs = len(obj_ids)

        boxes = []

        for i in range(num_objs):
            pos = np.where(masks[i])
            xmin = np.min(pos[1])
            xmax = np.max(pos[1])
            ymin = np.min(pos[0])
            ymax = np.max(pos[0])

            boxes.append([xmin, ymin, xmax, ymax])

        boxes = torch.as_tensor(boxes, dtype=torch.float32)

        labels = torch.ones((num_objs,), dtype=torch.int64)
        masks = torch.as_tensor(masks, dtype=torch.uint8)

        image_id = torch.tensor([idx])
        area = (boxes[:, 3] - boxes[:, 1]) * (boxes[:, 2] - boxes[:, 0])

        iscrowd = torch.zeros((num_objs,), dtype=torch.int64)

        target = {}
        target["boxes"] = boxes
        target["labels"] = labels
        target["masks"] = masks
        target["image_id"] = image_id
        target["area"] = area
        target["iscrowd"] = iscrowd

        if self.transform is not None:
            img, target = self.transform(img, target)

        return img, target

    def __len__(self):
        return len(self.imgs)


class BuildingDataset(torch.utils.data.Dataset):
    def __init__(self,images_dir,annotation_file,transforms=None):
        self.images_dir=images_dir
        self.annotation_file=annotation_file
        self.transform=transforms
        self.images_name=os.listdir(images_dir)
        with open(annotation_file) as f:
            self.labels_json=json.load(f)

    def __getitem__(self, i):
        image=cv2.imread(os.path.join(self.images_dir,self.images_name[i]))
        image=cv2.cvtColor(image,cv2.COLOR_BGR2RGB)

        label_info=self.labels_json[self.images_name[i]+'262144']
        annos=label_info['regions']

        boxes=[]
        labels=[]
        masks=[]

        for anno in annos:
            shape_attr=anno["shape_attributes"]
            px=shape_attr["all_points_x"]
            py=shape_attr["all_points_y"]
            poly=[(x+0.5,y+0.5) for x,y in zip(px,py)]
            poly=[p for x in poly for p in x]

            #将点坐标转换为mask二值图片
            rles=coco_mask.frPyObjects([poly],512,512)
            mask=coco_mask.decode(rles)

            category_id=1

            boxes.append([np.min(px),np.min(py),np.max(px),np.max(py)])
            labels.append(category_id)
            masks.append(mask.squeeze())

        image_id=torch.tensor([i])
        iscrowd=torch.zeros((len(annos),),dtype=torch.int64)

        boxes=torch.as_tensor(boxes,dtype=torch.float32)

        labels=torch.as_tensor(labels,dtype=torch.int64)
        masks=torch.as_tensor(masks,dtype=torch.uint8)

        target={}
        target["boxes"]=boxes
        target["labels"]=labels
        target["masks"]=masks
        target["image_id"]=image_id
        target["iscrowd"]=iscrowd

        if  self.transform is not None:
            image,target=self.transform(image,target)

        return image,target


    def __len__(self):
        return len(self.images_name)


def get_transform(train):
    transforms=[]

    transforms.append(T.ToTensor())
    if train:
        transforms.append(T.RandomHorizontalFlip(0.5))

    return T.Compose(transforms)

