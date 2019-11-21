import torch
import torch.nn as nn
import torch.nn.functional as F
from . import Swish


class EmptyLayer(nn.Module):
    def forward(self, x):
        return x


# weight standard conv
class WSConv2d(nn.Conv2d):
    def forward(self, x):
        weight = self.weight
        weight_mean = weight.mean(dim=1, keepdim=True)
        weight_mean = weight_mean.mean(dim=2, keepdim=True)
        weight_mean = weight_mean.mean(dim=3, keepdim=True)
        weight = weight - weight_mean

        var = torch.var(weight.view(weight.size(0), -1), dim=1,
                        unbiased=False).clamp(min=1e-12)
        std = torch.sqrt(var).view(-1, 1, 1, 1)
        weight = weight / std.expand_as(weight)
        return F.conv2d(x, weight, self.bias, self.stride, self.padding,
                        self.dilation, self.groups)


# conv norm swish
class CNS(nn.Module):
    def __init__(self,
                 in_channels,
                 out_channels,
                 ksize=3,
                 stride=1,
                 groups=1,
                 dilation=1,
                 activate=True):
        super(CNS, self).__init__()
        self.conv = WSConv2d(in_channels,
                             out_channels,
                             ksize,
                             stride=stride,
                             padding=(ksize - 1) // 2 - 1 + dilation,
                             groups=groups,
                             dilation=dilation,
                             bias=False)
        if out_channels % 32 == 0:
            self.norm = nn.GroupNorm(32, out_channels)
        elif out_channels % 8 == 0:
            self.norm = nn.GroupNorm(8, out_channels)
        else:
            self.norm = EmptyLayer()
        if activate:
            self.activation = Swish()
        else:
            self.activation = EmptyLayer()

    def forward(self, x):
        x = self.conv(x)
        x = self.norm(x)
        x = self.activation(x)
        return x
