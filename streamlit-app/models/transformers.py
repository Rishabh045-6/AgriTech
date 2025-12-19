import torch
import torch.nn as nn

class CropTransformer(nn.Module):
    def __init__(
        self,
        num_features,
        window_size,
        d_model=64,
        nhead=4,
        num_layers=2,
        num_classes=3,
        dropout=0.1
    ):
        super().__init__()

        self.input_proj = nn.Linear(num_features, d_model)

        self.pos_embed = nn.Parameter(
            torch.randn(1, window_size, d_model)
        )

        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=4 * d_model,
            dropout=dropout,
            batch_first=True
        )

        self.encoder = nn.TransformerEncoder(
            encoder_layer,
            num_layers=num_layers
        )

        self.head = nn.Sequential(
            nn.LayerNorm(d_model),
            nn.Linear(d_model, num_classes)
        )

    def forward(self, x):
        x = self.input_proj(x)
        x = x + self.pos_embed[:, :x.size(1)]
        x = self.encoder(x)
        x = x.mean(dim=1)
        return self.head(x)
