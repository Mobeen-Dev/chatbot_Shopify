import pickle

with open("bucket/products.pkl", "rb") as f:
    products = pickle.load(f)
    print(products['anycubic-full-metal-i3-mega-3d-printer-with-ultrabase-heatbed-and-3-5-inch-touch-screen'])