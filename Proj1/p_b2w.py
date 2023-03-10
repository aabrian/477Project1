from pupil_apriltags import Detector
import cv2
import numpy as np
import time
from robomaster import robot
from robomaster import camera
from math import(sin, cos, asin, pi, atan2, atan, acos)

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

def rotation_wa(theta):
    rot = np.array([[sin(theta),cos(theta),0], [0,0,-1], [-cos(theta),sin(theta),0]])
    return np.linalg.inv(rot)

if __name__ == '__main__':
    ep_robot = robot.Robot()
    ep_robot.initialize(conn_type="ap")
    ep_camera = ep_robot.camera
    ep_camera.start_video_stream(display=False, resolution=camera.STREAM_360P)

    tag_size=0.2 # tag size in meters

    ep_chassis = ep_robot.chassis

    l = .265
    tag_coords = {32:[-8.5*l,0],34:[-8*l,-1.5*l],33:[-7.5*l,0],31:[-7.5*l,2*l],35:[-6*l,2.5*l],
    36:[-4*l,2.5],42:[-2.5*l,2*l],44:[-2.5*l,2*l],46:[-2*l,-1.5*l],45:[-1.5*l,0,0]}

    while True:
        try:
            img = ep_camera.read_cv2_image(strategy="newest", timeout=1)   
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            gray.astype(np.uint8)

            kk = 1
            K=np.array([[184.752*kk, 0, 320], [0, 184.752*kk, 180], [0, 0, 1]])

            results = at_detector.detect(gray, estimate_tag_pose=False)

            for res in results:
                pose = find_pose_from_tag(K, res)
                # print('pose = ')
                # print(pose[0])
                id = int(res.tag_id)
                rot_ca, jaco = cv2.Rodrigues(pose[1], pose[1])
                # print('rot = ')
                # print(rot_ca)
                pts = res.corners.reshape((-1, 1, 2)).astype(np.int32)
                img = cv2.polylines(img, [pts], isClosed=True, color=(0, 0, 255), thickness=5)
                cv2.circle(img, tuple(res.center.astype(np.int32)), 5, (0, 0, 255), -1)
                T_ca = np.array([[rot_ca[0][0],rot_ca[0][1],rot_ca[0][2],pose[0][0]],[rot_ca[1][0],rot_ca[1][1],rot_ca[1][2],pose[0][1]],[rot_ca[2][0],rot_ca[2][1],rot_ca[2][2],pose[0][2]],[0,0,0,1]])
                T_ac = np.linalg.inv(T_ca)
                # print(T_ca)
                time.sleep(.5)
                x_pos = pose[0][2]
                y_pos = pose[0][0]
                print()
                rot_wa = rotation_wa(tag_coords[45][2])
                print(rot_wa)
                rot_ac = np.transpose(rot_ca)
                rot_wc = np.matmul(rot_wa, rot_ac)
                rot_bc = np.array([[0, 0, 1], [1, 0, 0], [0, -1, 0]])
                w2b = np.matmul(rot_bc,np.transpose(rot_wc))
                v_w = np.array([1,0,0])
                kb = 0.25
                v_b = kb*np.matmul(w2b,v_w)
                cv2.circle(img, tuple(res.center.astype(np.int32)), 5, (0, 0, 255), -1)
                pose[0][1]= 0
                Tag_loc = pose[0]
                Dtag_loc = [0, 0, 1]

                cross_product_AB = np.cross(Tag_loc, Dtag_loc)
                mag_cross = np.linalg.norm(cross_product_AB)
            
                dot_AB = np.dot(Tag_loc,Dtag_loc)


                if pose[0][0] < 0:
                    theta = -(np.arctan2(mag_cross, dot_AB))*180/np.pi
                else:
                    theta = (np.arctan2(mag_cross, dot_AB))*180/np.pi
                kt = 1
                # ep_chassis.drive_speed(x = v_b[1], y = v_b[0], z=kt*theta, timeout=.5)

            cv2.imshow("img", img)
            cv2.waitKey(10)
           
        except KeyboardInterrupt:
            ep_camera.stop_video_stream()
            ep_robot.close()
            print ('Exiting')
            exit(1)


