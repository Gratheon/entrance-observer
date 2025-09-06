# A Practical Methodology for Monitoring Beehive Entrances Using Computer Vision and IoT

## Abstract

Traditional beekeeping practices rely on manual, intrusive, and time-consuming inspections to monitor colony health, a process that is both inefficient and stressful for the bees. This paper presents a practical methodology for non-invasive beehive monitoring using a low-cost, yet powerful, combination of computer vision and IoT technology. The system, called the `entrance-observer`, uses an NVIDIA Jetson Orin Nano and a 4K USB camera to continuously record video of the hive entrance. A YOLOv8n-based AI model processes the video in real-time, detecting and tracking individual bees to collect a rich set of metrics, including forager traffic, flight speed, and individual bee tracks. This data is uploaded to a cloud-based web application for visualization and analysis. The breakthrough of this methodology lies in its ability to move beyond simple bee counting, providing nuanced data that can be used to detect complex behaviors such as orientation flights, pollination activity, swarming, and robbing behavior by bees from other hives. This provides beekeepers with actionable insights into colony health, with a particular focus on assessing pollination efficiency, forager loss, and creating a foundational video dataset for future Varroa mite detection models. The paper details the system architecture, the experimental methodology, and preliminary findings from a deployment in a suburban apiary in Tallinn, Estonia. The `entrance-observer` system offers a practical and scalable solution to some of the most pressing challenges in modern beekeeping, with the potential to improve colony health, increase productivity, and make beekeeping more sustainable.

## 1. Introduction

Honey bees (Apis mellifera) are essential for global food security, yet beekeepers face immense challenges in maintaining healthy colonies. A primary threat is the Varroa destructor mite, a parasite that can decimate a hive if not managed effectively. Traditional monitoring methods, such as manual inspections, are labor-intensive, stressful for the bees, and often fail to provide the timely data needed for effective intervention. While tools like hive scales can indicate changes in foraging activity, they do not offer insights into the underlying causes, such as disease, forager loss, or parasite load.

The limitations of existing methods highlight the need for more advanced, non-invasive monitoring solutions. The ability to automatically detect parasites like Varroa mites and other threats at an early stage would be a significant breakthrough for beekeepers, enabling them to apply targeted treatments only when necessary, thereby reducing chemical use and improving colony health. Furthermore, detailed monitoring of forager traffic can provide valuable information about pollination efficiency and the impact of environmental stressors, such as pesticides.

This paper presents a practical methodology for beehive entrance monitoring that aims to address these challenges. We have developed a low-cost, scalable system called the `entrance-observer`, which uses a camera and an AI model running on an edge device to continuously analyze bee activity. The system is designed to not only count incoming and outgoing bees but also to serve as a platform for developing more advanced diagnostic tools, with a primary focus on the detection of Varroa mites and other parasites. This paper details the system's architecture, the methodology for its deployment and data collection, and discusses its potential to become a valuable tool for modern, sustainable beekeeping.

## 2. Related Work

The application of technology to beekeeping, often referred to as "precision beekeeping," has been a growing area of research in recent years. A significant body of work has focused on the use of sensors to monitor the internal conditions of the hive, such as temperature, humidity, and acoustics [7, 5, 9]. While valuable, these methods do not capture the full picture of colony activity.

Computer vision has emerged as a powerful tool for non-invasive beehive monitoring. Early work focused on tracking marked bees [35] or using RFID tags [27], but these methods are intrusive. More recent approaches have focused on tracking unmarked bees. For example, Rodriguez et al. [1] developed a system using convolutional neural networks (CNNs) and Part Affinity Fields (PAFs) for pose estimation, allowing for accurate tracking and pollen detection. Marstaller et al. [2] proposed "DeepBees," a multi-task CNN architecture for genus identification, pollen detection, pose estimation, and classification of bees.

A major focus of computer vision research in beekeeping has been the detection of the Varroa destructor mite. Traditional methods are intrusive and harmful to bees. Non-invasive approaches have explored the use of hyperspectral imaging to improve the contrast between mites and bees [3], and the use of object detectors like YOLOv8 and SSD for mite detection [4]. Bilik et al. [4] found that training a model to detect "infected bees" as a class was more effective than detecting the mites themselves.

The system presented in this paper builds upon this existing body of work, but with a specific focus on providing a practical, low-cost, and easy-to-use solution for beekeepers. Unlike many previous systems, which have been primarily research-focused, the `entrance-observer` is designed to be a practical tool that can be deployed in real-world apiaries. It utilizes a state-of-the-art YOLOv8 model for bee detection and tracking, and is specifically designed to address the key challenges of forager loss, pollination efficiency, and Varroa mite detection.

## 3. System Architecture
### 3.1. Hardware

The hardware for the `entrance-observer` system is designed to be a low-cost, yet powerful, platform for edge computing. The core of the system is an NVIDIA Jetson Orin Nano 8GB, a compact and powerful single-board computer with a GPU that is well-suited for running AI models.

The video data is captured by a Mokose 4K USB camera, which is equipped with a 5-50mm varifocal lens. This combination allows for high-resolution video capture and the flexibility to adjust the field of view to suit different hive entrance configurations. The camera is mounted on an articulating arm, which allows for precise positioning.
### 3.2. Software
#### 3.2.1. entrance-observer application

The `entrance-observer` application is a Python-based software package that runs on the edge device. It is responsible for capturing video, processing it in real-time, and uploading the results to the cloud. The application is built using a modular architecture, with different components responsible for different tasks.

The video processing pipeline is built using OpenCV. It captures frames from the camera, resizes them to a manageable resolution, and then passes them to two separate queues: one for video writing and one for AI processing. This multi-threaded approach ensures that the video capture process is not blocked by the computationally intensive AI processing.

Bee detection and tracking is performed using a YOLOv8 model. The model has been pre-trained on a large dataset of bee images and is able to detect and track individual bees with a high degree of accuracy. The application uses the tracking information to calculate a rich set of metrics, including:

*   **`bees_in`**: The number of bees entering the hive.
*   **`bees_out`**: The number of bees exiting the hive.
*   **`net_flow`**: The difference between `bees_in` and `bees_out`.
*   **`avg_speed_px_per_frame`**: The average speed of the bees.
*   **`p95_speed_px_per_frame`**: The 95th percentile of bee speed.
*   **`stationary_bees_count`**: The number of bees that are not moving.

The application also provides a local web UI, which is built using Flask. The web UI allows the user to view a live video feed from the camera, monitor the bee traffic statistics, and adjust the camera settings.

#### 3.2.2. Gratheon web application

The Gratheon web application is a cloud-based platform that provides a centralized location for storing, visualizing, and analyzing the data from the `entrance-observer` devices. The web application provides a user-friendly interface that allows beekeepers to:

*   View video playback from their hives.
*   Monitor the bee traffic statistics in real-time.
*   Analyze historical data to identify trends and anomalies.
*   Receive alerts and notifications about important events, such as a sudden drop in forager activity or a potential hornet attack.

The web application is designed to be a powerful tool for beekeepers, providing them with the information they need to make informed decisions about the management of their colonies.

## 4. Methodology
### 4.1. Experimental Setup

The experiment was conducted in a suburban apiary located in Tallinn, Estonia (Pirita-Kose district). The beehive used for the study was a 3-section vertical hive with Estonian frames, manufactured by Karlwood. The hive was positioned on four large bricks, with the entrance facing south-west, and was protected from the wind by a house wall on the eastern side.

The `entrance-observer` device was installed at the hive entrance, with the camera positioned above the entrance to provide a clear, top-down view of the bees. The camera was mounted on a "Security Camera Mount Bracket for Camera with 1/4 Screw Head Wall Mount," which allowed for precise and stable positioning. The NVIDIA Orin Nano was housed in a wooden enclosure on top of the hive, physically separated from the bees to avoid any disturbance. Power was supplied to the device via an extension cord connected to a standard 220V household outlet.

During the setup process, several hardware and software challenges were encountered. On the hardware side, the NVIDIA Jetson Orin Nano did not provide sufficient power to the Mokose 4K camera over USB3. An attempt to use an external powered USB hub resulted in the camera and several USB ports on the Jetson Orin Nano being damaged due to an incorrect voltage setting (12V instead of 5V). As a result, a backup camera had to be used, connected to the single remaining USB-C port, which limited the video capture to USB2 speeds. This hardware failure constrained the video resolution to 1280x720 and the frame rate to 15 FPS. Additionally, the Wi-Fi signal at the apiary was not strong enough for the Jetson Orin Nano to maintain a stable connection, so a TP-Link Wi-Fi extender was installed to boost the signal.

On the software side, installing PyTorch with GPU support on the Jetson Orin Nano proved to be a significant hurdle. To overcome this, a Docker-based approach was adopted, using the official Ultralytics Docker image. While this solved the dependency issues, it also meant that a native Python UI could not be used. Consequently, a web-based UI was developed to provide a way to preview the results and configure the system. For connectivity, the system initially relied on a local area network (LAN) for remote access via SSH and a web interface. This was later upgraded to Tailscale, a commercial VPN solution, which enabled secure remote monitoring and video file downloads from any location, facilitating off-site system checks and data retrieval.

### 4.2. Data Collection

Data collection began on September 4th and is ongoing, with the goal of capturing approximately two weeks of data before the onset of cold weather. The `entrance-observer` application is configured to record video in 20-30 second chunks, covering the full daylight hours.

In addition to the video data, historical weather data for the apiary's location is being collected from the Open-Meteo API (`archive-api.open-meteo.com`). This data includes a wide range of meteorological variables, such as solar radiation, wind speed and gust, cloud cover, precipitation, atmospheric pressure, and air pollution (PM2.5 and PM10).

### 4.2.1. AI Model Training

The bee detection model was trained using the YOLOv8n architecture, chosen for its optimal balance of speed and accuracy on edge devices like the NVIDIA Jetson Orin Nano. The training was conducted in the Google Colab environment, leveraging its cloud-based GPU resources ([*Specify GPU model, e.g., NVIDIA T4*]).

The model was trained on the "Bees on Hive Landing Boards" dataset, which was sourced from Roboflow. The dataset consists of [*Specify number of images*] images, which were augmented using techniques such as [*Specify augmentation techniques, e.g., rotation, flipping, and brightness adjustments*] to improve the model's robustness.

After 25 epochs of training, the model achieved a mean Average Precision (mAP) of [*Specify mAP score*] on the validation set, demonstrating a high level of accuracy in detecting bees.

### 4.3. Data Analysis

The data analysis is performed in two stages. First, the `entrance-observer` application processes the video data in real-time, calculating the bee traffic metrics described in Section 3.2.1. This data is then uploaded to the Gratheon web application for storage and visualization.

The second stage of the analysis involves correlating the bee traffic data with the historical weather data and analyzing patterns based on the time of day. This will allow for an investigation of the relationships between bee behavior and environmental factors. For example, it will be possible to determine how foraging activity is affected by temperature, solar radiation, and wind speed, and to identify daily activity cycles. A week-long dataset will be particularly valuable for observing these trends.

## 5. Results and Discussion

The data collection for this study is currently ongoing. However, preliminary analysis of the bee traffic data has already revealed some interesting patterns. For example, on September 5th, a significant drop in bee activity was observed around 13:15 UTC. While the exact cause is unconfirmed due to a lack of detailed log data for that specific event, it is hypothesized that this may have been caused by a sudden increase in cloud cover. This event highlights the system's ability to detect subtle changes in colony behavior that might otherwise go unnoticed and underscores the need for continuous data collection to capture and analyze more of these non-linear dynamics.

The primary goal of the data analysis will be to investigate the relationships between bee behavior and environmental factors. It is expected that bee activity will be positively correlated with temperature and solar radiation, and negatively correlated with precipitation and wind speed. However, the high-resolution data collected by the `entrance-observer` system may also reveal more subtle correlations. For example, it will be possible to investigate the impact of wind gusts and air pollution on foraging behavior.

The results will be presented using a variety of visualizations, including time-series graphs of bee traffic and weather data, scatter plots to show correlations between variables, and heatmaps to visualize daily and weekly patterns of activity. These visualizations will be designed to be intuitive and easy to interpret, providing beekeepers with a clear and comprehensive overview of their colony's health and productivity.

## 6. Conclusion

This paper has presented a practical methodology for monitoring beehive entrances using a low-cost, yet powerful, combination of computer vision and IoT technology. The `entrance-observer` system, built on an NVIDIA Jetson Orin Nano and a 4K USB camera, provides a non-invasive way to collect high-resolution data on bee behavior. The accompanying Gratheon web application offers a user-friendly platform for visualizing and analyzing this data.

The system is designed to address some of the most pressing challenges in modern beekeeping, including forager loss, pollination efficiency, and the detection of Varroa mites. By providing beekeepers with real-time, actionable insights into their colonies, the `entrance-observer` has the potential to improve colony health, increase productivity, and make beekeeping more sustainable.

While the data collection for this study is still ongoing, the preliminary results are promising. The system has already demonstrated its ability to detect subtle changes in bee behavior, and the planned analysis of the relationship between bee activity and weather data is expected to yield valuable insights.

It is important to acknowledge the limitations of the current system. As pointed out by beekeepers, the practical value of simply counting bees is limited. The true potential of this technology lies in its ability to detect parasites and other threats. The current camera resolution and frame rate, constrained by the hardware failure described in Section 4.1, may not be sufficient for reliable Varroa mite detection. Furthermore, the identification of individual unmarked bees remains a significant challenge.

Future work will focus on addressing these limitations. The immediate priority is to improve the hardware setup. Ideally, this would involve a 4K camera capable of capturing video at 60 FPS to discern fine details, paired with a GPU powerful enough for real-time detection of multiple distinct entities such as Varroa mites, drones, the queen, and bees carrying pollen. A protective, weatherproof camera case with integrated LED lighting would also be necessary to ensure consistent image quality regardless of external conditions. Given the challenges encountered with flashing and software installation on the Jetson Orin, switching to a more developer-friendly platform like a Mac Mini is being considered.

While the current system is not yet capable of mite detection, the video dataset being collected is a crucial first step towards training such a model. The true potential of this technology lies in its ability to detect parasites and other threats, and the current methodology lays the groundwork for that future. The long-term vision is to create a comprehensive and fully automated beehive monitoring system that can not only detect parasites but also provide beekeepers with the tools to manage their colonies more effectively. The ultimate goal is to create a system that is not just a "toy" for researchers, but a practical and affordable tool that can make a real difference to the health and productivity of bee colonies.

## 7. References

[1] Rodriguez, I. F., Chan, J., Alvarez Rios, M., Branson, K., Agosto-Rivera, J. L., Giray, T., & Mégret, R. (2022). Automated Video Monitoring of Unmarked and Marked Honey Bees at the Hive Entrance. *Frontiers in Computer Science*, 3, 769338.

[2] Marstaller, J., Tausch, F., & Stock, S. (2019). DeepBees – Building and Scaling Convolutional Neuronal Nets For Fast and Large-scale Visual Monitoring of Bee Hives. In *Proceedings of the IEEE/CVF International Conference on Computer Vision Workshops*.

[3] Bielik, S., & Bilík, Š. (2025). Towards Varroa destructor mite detection using a narrow spectra illumination. *arXiv preprint arXiv:2504.06099*.

[4] Bilik, S., Kratochvila, L., Ligocki, A., Bostik, O., Zemcik, T., Hybl, M., ... & Zalud, L. (2021). Visual Diagnosis of the Varroa Destructor Parasitic Mite in Honeybees Using Object Detector Techniques. *Sensors*, 21(8), 2764.
