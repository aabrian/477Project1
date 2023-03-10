from pupil_apriltags import Detector
import cv2
import numpy as np
import time
from robomaster import robot
from robomaster import camera

at_detector = Detector(
    families="tag36h11",
    nthreads=1,
    quad_decimate=1.0,
    quad_sigma=0.0,
    refine_edges=1,
    decode_sharpening=0.25,
    debug=0
)

def find_pose_from_tag(K, detection):
    m_half_size = tag_size / 2

    marker_center = np.array((0, 0, 0))
    marker_points = []
    marker_points.append(marker_center + (-m_half_size, m_half_size, 0))
    marker_points.append(marker_center + ( m_half_size, m_half_size, 0))
    marker_points.append(marker_center + ( m_half_size, -m_half_size, 0))
    marker_points.append(marker_center + (-m_half_size, -m_half_size, 0))
    _marker_points = np.array(marker_points)

    object_points = _marker_points
    image_points = detection.corners

    pnp_ret = cv2.solvePnP(object_points, image_points, K, distCoeffs=None,flags=cv2.SOLVEPNP_IPPE_SQUARE)
    if pnp_ret[0] == False:
        raise Exception('Error solving PnP')

    r = pnp_ret[1]
    p = pnp_ret[2]

    return p.reshape((3,)), r.reshape((3,))
def find_robot_pos(tag_coord,tag_orientation,robot_tag_pose):
    world_pos = [0,0]
    if tag_orientation == 'right':
        world_pos[0] = tag_coord[0]+robot_tag_pose[2]
        world_pos[1] = tag_coord[1]-robot_tag_pose[0]
    if tag_orientation == 'left':
        world_pos[0] = tag_coord[0]-robot_tag_pose[2]
        world_pos[1] = tag_coord[1]+robot_tag_pose[0]
    if tag_orientation == 'down':
        world_pos[0] = tag_coord[0]-robot_tag_pose[0]
        world_pos[1] = tag_coord[1]+robot_tag_pose[0]
    if tag_orientation == 'up':
        world_pos[0] = tag_coord[0]+robot_tag_pose[2]
        world_pos[1] = tag_coord[1]-robot_tag_pose[0]        
    return world_pos


if __name__ == '__main__':
    ep_robot = robot.Robot()
    ep_robot.initialize(conn_type="ap")
    ep_camera = ep_robot.camera
    ep_camera.start_video_stream(display=False, resolution=camera.STREAM_360P)
    ep_chassis = ep_robot.chassis

    tag_size=0.2 # tag size in meters
    l = .265
    tag_coords = {32 : [-8.5*l,0],34:[-8*l,-1.5*l],33:[-7.5*l,0],31:[-7.5*l,2*l],35:[-6*l,2.5*l],
36:[-4*l,2.5*l],42:[-2.5*l,2*l],44:[-2.5*l,0],46:[-2*l,-1.5*l],45:[-1.5*l,0],39:[-4.5*l,-2*l],41:[-4.5*l,-4*l],43:[-1.5*l,2*l],37:[-5*l,-0.5*l]}
    tag_orientation  = {30:'left',32:'left',34:'down',33:'right',31:'right',35:'down',36:'down',42:'left',
                        44:'left',46:'down',45:'right',43:'right',37:'up',38:'left',40:'left',39:'right',41:'right'}
    while True:
        try:
            img = ep_camera.read_cv2_image(strategy="newest", timeout=2)   
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            gray.astype(np.uint8)

            K=np.array([[184.752, 0, 320], [0, 184.752, 180], [0, 0, 1]])

            results = at_detector.detect(gray, estimate_tag_pose=False)
           

            for res in results:
                current_tag = (res.tag_id)
                pose = find_pose_from_tag(K, res)
                rot, jaco = cv2.Rodrigues(pose[1], pose[1])
                # print(rot)
                pts = res.corners.reshape((-1, 1, 2)).astype(np.int32)
                img = cv2.polylines(img, [pts], isClosed=True, color=(0, 0, 255), thickness=5)
                cv2.circle(img, tuple(res.center.astype(np.int32)), 5, (0, 0, 255), -1)
                # print((pose[0]))
                print(current_tag)
                world_pose = find_robot_pos(tag_coords[current_tag],tag_orientation[current_tag],pose[0])
                print(world_pose)

                time.sleep(1)



            cv2.imshow("img", img)
            cv2.waitKey(10)

        except KeyboardInterrupt:
            ep_camera.stop_video_stream()
            ep_robot.close()
            print ('Exiting')
            exit(1)