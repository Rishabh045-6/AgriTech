import torch
import torch.nn as nn

class TransformerClassifier(nn.Module):
    def __init__(self, input_dim, seq_len, num_classes=3,
                 d_model=64, nhead=4, num_layers=3, dropout=0.1):
        super().__init__()

        self.input_proj = nn.Linear(input_dim, d_model)
        self.d_model = d_model
        self.num_classes = num_classes

        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=128,
            dropout=dropout,
            batch_first=True
        )

        self.encoder = nn.TransformerEncoder(encoder_layer, num_layers)

        self.head = nn.Sequential(
            nn.LayerNorm(d_model),
            nn.Linear(d_model, 64),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(64, num_classes)
        )

    def forward(self, x):
        # x shape: (batch_size, seq_len, input_dim)
        x = self.input_proj(x)
        
        # Create positional embedding dynamically based on sequence length
        batch_size, actual_seq_len, d_model = x.shape
        pos_emb = torch.zeros(1, actual_seq_len, d_model, device=x.device)
        x = x + pos_emb
        
        x = self.encoder(x)
        x = x.mean(dim=1)
        return self.head(x)