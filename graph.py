import json
import os
import requests
import tkinter as tk
from pyvis.network import Network
from PIL import Image, ImageDraw
from io import BytesIO
from urllib.parse import urlparse

cwd = os.getcwd()
# select file
root = tk.Tk()
root.withdraw()
filename = filedialog.askopenfilename(initialdir=cwd, title="Choose your generated json file", filetypes=[("JSON file", "*.json")])

# Load JSON data
with open(filename, 'r') as f:
    friends = json.load(f)

# Create a directory to store avatars
os.makedirs("avatars", exist_ok=True)

# Helper function to download and make images circular
def make_circular(image_url):
    try:
        # Extract filename from URL
        parsed = urlparse(image_url)
        filename = os.path.basename(parsed.path)
        output_path = f"avatars/circular_{filename}"

        # Skip if already downloaded
        if os.path.exists(output_path):
            return output_path

        # Download with retries
        for _ in range(3):  # Retry up to 3 times
            try:
                response = requests.get(image_url, timeout=10)
                response.raise_for_status()  # Raise error for bad status
                img = Image.open(BytesIO(response.content)).convert("RGBA")

                # Create circular mask
                mask = Image.new("L", img.size, 0)
                draw = ImageDraw.Draw(mask)
                draw.ellipse((0, 0, img.size[0], img.size[1]), fill=255)
                img.putalpha(mask)

                # Save
                img.save(output_path)
                return output_path
            except requests.exceptions.RequestException as e:
                print(f"Retrying {image_url} due to error: {e}")
                continue
        return None
    except Exception as e:
        print(f"Failed to process {image_url}: {e}")
        return None

# Create a Pyvis network
net = Network(
    notebook=False,
    height="750px",
    width="100%",
    bgcolor="#222222",
    font_color="white",
    directed=False,
)

# Add nodes (friends) with circular profile pictures
for friend_id, friend_info in friends.items():
    name = friend_info["name"]
    mutual_count = len(friend_info["mutual"])
    avatar_url = friend_info["avatar"]

    # Make the avatar circular
    circular_avatar = make_circular(avatar_url)
    if not circular_avatar:
        # Fallback to default avatar
        default_avatar_url = f"https://cdn.discordapp.com/embed/avatars/{int(friend_id) % 5}.png"
        circular_avatar = make_circular(default_avatar_url)

    # Add node
    label = f"{name}\n({mutual_count} mutual)"
    net.add_node(
        friend_id,
        label=label,
        shape="circularImage",
        image=circular_avatar,
        title=f"Mutual servers: {mutual_count}",
        size=mutual_count * 5 + 10,
    )

# Add edges (connections between friends who share servers)
server_to_friends = {}
for friend_id, friend_info in friends.items():
    for server_id in friend_info["mutual"]:
        if server_id not in server_to_friends:
            server_to_friends[server_id] = []
        server_to_friends[server_id].append(friend_id)

for server_id, friend_list in server_to_friends.items():
    for i in range(len(friend_list)):
        for j in range(i + 1, len(friend_list)):
            friend_a = friend_list[i]
            friend_b = friend_list[j]
            shared_servers = set(friends[friend_a]["mutual"]) & set(friends[friend_b]["mutual"])
            if shared_servers:
                net.add_edge(
                    friend_a,
                    friend_b,
                    value=len(shared_servers),
                    title=f"Shared servers: {len(shared_servers)}",
                )

# Customize physics
net.set_options("""
{
  "physics": {
    "forceAtlas2Based": {
      "gravitationalConstant": -50,
      "centralGravity": 0.01,
      "springLength": 150,
      "springConstant": 0.08
    },
    "minVelocity": 0.75,
    "solver": "forceAtlas2Based"
  }
}
""")

# Save and show
net.show("discord_friends_network.html", notebook=False)
print("Graph saved as 'discord_friends_network.html'. Open it in a browser.")
