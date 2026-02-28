from predict_crop_stage import predict_crop_analysis_new

print(predict_crop_analysis_new('test','wheat',[
    {'latitude':10,'longitude':20},
    {'latitude':10.1,'longitude':20.1},
    {'latitude':10.2,'longitude':20.2}
]))
