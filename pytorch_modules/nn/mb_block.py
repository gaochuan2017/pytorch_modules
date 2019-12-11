from random import random
import torch
import torch.nn as nn
import torch.nn.functional as F
from . import Swish, CNS, SELayer, EmptyLayer, DropConnect, WSConv2d


class MbBlock(nn.Module):
    def __init__(self,
                 in_channels,
                 out_channels,
                 ksize=3,
                 stride=1,
                 dilation=1,
                 expand_ratio=6,
                 drop_rate=0.2,
                 se=True,
                 reps=1, ):
        super(MbBlock, self).__init__()
        blocks = [
            MbConv(in_channels, out_channels, ksize, stride, dilation,
                   expand_ratio, drop_rate, se)
        ]
        for i in range(reps):
            blocks.append(
                MbConv(out_channels, out_channels, ksize, 1, dilation,
                       expand_ratio, drop_rate, se))
        self.blocks = nn.Sequential(*blocks)

    def forward(self, x):
        return self.blocks(x)


class MbConv(nn.Module):
    def __init__(self,
                 in_channels,
                 out_channels,
                 ksize=3,
                 stride=1,
                 dilation=1,
                 expand_ratio=6,
                 drop_rate=0.2,
                 se=True):
        super(MbConv, self).__init__()
        mid_channels = in_channels * expand_ratio
        if in_channels == out_channels and stride == 1:
            self.add = True
        else:
            self.add = False
        self.block = nn.Sequential(
            CNS(in_channels, mid_channels, 1)
            if expand_ratio > 1 else EmptyLayer(),
            CNS(mid_channels,
                mid_channels,
                ksize=ksize,
                stride=stride,
                groups=mid_channels,
                dilation=dilation),
            SELayer(mid_channels) if se else EmptyLayer(),
            # no activation, see https://arxiv.org/pdf/1604.04112.pdf
            CNS(mid_channels, out_channels, 1, activate=False),
            DropConnect(drop_rate) if drop_rate > 0 and self.add else EmptyLayer(),
        )

    def forward(self, x):
        f = self.block(x)
        if self.add:
            f += x
        return f