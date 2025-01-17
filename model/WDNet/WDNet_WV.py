import torch
from utils import clamp
from generate_wm import generate_watermark,generate_watermark_ori
import torch.nn.functional as F

class WDNet_WV(object):
    def __init__(self,model,args,epsilon,start_epsilon,step_alpha,upper_limit,lower_limit):
        self.model = model
        self.epsilon = epsilon
        self.start_epsilon = start_epsilon
        self.step_alpha = step_alpha
        self.upper_limit = upper_limit
        self.lower_limit = lower_limit
        self.args = args

    def Clean(self,img_source,logo_path,seed):
        wm = clamp(img_source, self.lower_limit, self.upper_limit)
        wm, mask = generate_watermark_ori(img_source, logo_path, seed)
        wm = torch.unsqueeze(wm.cuda(), 0)
        clean_pred, clean_mask, alpha, w, _ = self.model(wm)
        return wm,clean_pred,clean_mask

    def RN(self,img_source,logo_path,seed):
        random_noise = torch.zeros_like(img_source).cuda()
        for i in range(len(self.epsilon)):
            random_noise[:, i, :, :].uniform_(-self.start_epsilon[i][0][0].item(), self.start_epsilon[i][0][0].item())
        wm_r = clamp(img_source + random_noise, self.lower_limit, self.upper_limit)
        wm_r, _ = generate_watermark_ori(wm_r, logo_path, seed)
        wm_r = torch.unsqueeze(wm_r.cuda(), 0)
        random_pred, clean_mask, alpha, w, _ = self.model(wm_r)
        return wm_r,random_pred, clean_mask


    def DWV(self,img_source,logo_path,seed):
        delta1 = torch.zeros_like(img_source).cuda()
        delta1.requires_grad = True
        for i in range(self.args.attack_iter):
            start_pred_target, start_mask, start_alpha, start_w, start_I_watermark = self.model(img_source + delta1)
            loss = F.mse_loss(img_source.data, start_pred_target.float())
            loss.backward()
            grad = delta1.grad.detach()
            d = delta1
            d = clamp(d + self.step_alpha * torch.sign(grad), -self.epsilon, self.epsilon)
            delta1.data = d
            delta1.grad.zero_()
        adv1 = clamp(img_source + delta1, self.lower_limit, self.upper_limit)
        adv1, _ = generate_watermark_ori(adv1, logo_path, seed)
        adv1 = torch.unsqueeze(adv1.cuda(), 0)
        adv1_pred, adv1_mask, alpha, w, _ = self.model(adv1)
        return adv1,adv1_pred,adv1_mask

    def IWV(self,img_source,logo_path,seed):
        mask_black = torch.zeros((1, 256, 256)).cuda()
        mask_black = torch.unsqueeze(mask_black, 0)

        delta2 = torch.zeros_like(img_source).cuda()
        delta2.requires_grad = True
        for i in range(self.args.attack_iter):
            start_pred_target, start_mask, start_alpha, start_w, start_I_watermark = self.model(img_source + delta2)
            loss = 2 * F.mse_loss(img_source.data, start_pred_target.float()) + F.mse_loss(mask_black.data,
                                                                                           start_mask.float())
            loss.backward()
            grad = -delta2.grad.detach()
            d = delta2
            d = clamp(d + self.step_alpha * torch.sign(grad), -self.epsilon, self.epsilon)
            delta2.data = d
            delta2.grad.zero_()
        adv2 = clamp(img_source + delta2, self.lower_limit, self.upper_limit)
        adv2, _ = generate_watermark_ori(adv2, logo_path, seed)
        adv2 = torch.unsqueeze(adv2.cuda(), 0)
        adv2_pred, adv2_mask, alpha, w, _ = self.model(adv2)
        return adv2,adv2_pred, adv2_mask