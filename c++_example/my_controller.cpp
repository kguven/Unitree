#include "control_parms.hpp"

void Custom::my_controller()
{


    for (int i = 0; i < 29; i++)
        {
            qref[i] = q_init[i];
            dqref[i] = 0;
            kp[i] = 50.0;
            kd[i] = 2;
            tau[i] = 0;
        }
    //Example of setting control parameters
    // if (running_time < 3.0)
    // {
    //     phase = tanh(running_time / 1.2);
    //     for (int i = 0; i < 12; i++)
    //     {
    //         qref[i] = phase * stand_up_joint_pos[i] + (1 - phase) * stand_down_joint_pos[i];
    //         dqref[i] = 0;
    //         kp[i] = phase * 50.0 + (1 - phase) * 20.0;
    //         kd[i] = 3.5;
    //         tau[i] = 0;
    //     }
    // }
    // else
    // {
    //     phase = tanh((running_time - 3.0) / 1.2);
    //     for (int i = 0; i < 12; i++)
    //     {
    //         qref[i] = phase * stand_down_joint_pos[i] + (1 - phase) * stand_up_joint_pos[i];
    //         dqref[i] = 0;
    //         kp[i] = 50;
    //         kd[i] = 3.5;
    //         tau[i] = 0;
    //     }
    // }

    //Example on accessing sensor values
    
    // std::cout << "\n--- ROBOT STATE ---\n";

    // std::cout << "q (joint positions): ";
    // for (int i = 0; i < 29; i++) std::cout << q[i] << " ";
    // std::cout << "\n";

    // std::cout << "dq (joint velocities): ";
    // for (int i = 0; i < 29; i++) std::cout << dq[i] << " ";
    // std::cout << "\n";

    // std::cout << "quaternion (w, x, y, z): ";
    // for (int i = 0; i < 4; i++) std::cout << quaternion[i] << " ";
    // std::cout << "\n";

    // std::cout << "gyroscope (x, y, z): ";
    // for (int i = 0; i < 3; i++) std::cout << gyroscope[i] << " ";
    // std::cout << "\n";

    // std::cout << "accelerometer (x, y, z): ";
    // for (int i = 0; i < 3; i++) std::cout << accelerometer[i] << " ";
    // std::cout << "\n";
}
