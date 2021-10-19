/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/. */

package config

import (
	"database/sql/driver"
	"time"
)

type SinkConfig struct {
	SinkID          string          `json:"sink_id"`
	OwnerID         string          `json:"owner_id"`
	Url             string          `json:"remote_host"`
	User            string          `json:"username"`
	Password        string          `json:"password"`
	State           PrometheusState `json:"state,omitempty"`
	Msg             string          `json:"msg,omitempty"`
	LastRemoteWrite time.Time       `json:"last_remote_write,omitempty"`
}

const (
	Unknown PrometheusState = iota
	Connected
	Error
	Idle
)

type PrometheusState int

var promStateMap = [...]string{
	"unknown",
	"connected",
	"error",
	"idle",
}

var promStateRevMap = map[string]PrometheusState{
	"unknown":   Unknown,
	"connected": Connected,
	"error":     Error,
	"idle":      Idle,
}

func (p PrometheusState) String() string {
	return promStateMap[p]
}

func (p *PrometheusState) Scan(value interface{}) error {
	*p = promStateRevMap[string(value.([]byte))]
	return nil
}

func (p PrometheusState) Value() (driver.Value, error) {
	return p.String(), nil
}
